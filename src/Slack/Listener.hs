{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE ScopedTypeVariables #-}
{-# LANGUAGE TypeFamilies #-}
{-# LANGUAGE TemplateHaskell #-}
module Slack.Listener where

import Control.Monad
import Data.Maybe
import Data.Monoid
import Data.List.NonEmpty (NonEmpty(..))
import GHC.Generics

import Control.Monad.STM
import Control.Concurrent
import Control.Concurrent.STM.TBQueue
import Control.Exception.Safe
import Control.Monad.Base
import Control.Monad.Logger
import Control.Monad.Reader
import Control.Monad.Trans.Control
import Data.HashMap.Strict (HashMap)
import Data.Time
import Data.Time.Clock.POSIX
import Network.Wreq
import Caching.ExpiringCacheMap.HashECM
import Control.Lens
import Data.Aeson
import Data.Aeson.Types
import Control.Concurrent.Async.Lifted.Safe
import Data.Text (Text)
import qualified Data.Text as T
import Wuss hiding (Config)
import Network.WebSockets (ClientApp, receiveData, sendClose, sendTextData, ConnectionException (..))
import Network.URI

import Configuration
import Monitoring.Sentry
import Monitoring.Sentry.Configuration
import Slack.Types
import Slack.Utilities hiding (sendMessage)
import GroupMe.Types
import GroupMe.Utilities
import Types
import Utilities


startWsListener :: (MonadReader r m, HasConfig r, MonadIO m, MonadBaseControl IO m, MonadLogger m, Forall (Pure m), MonadCatch m) => m ()
startWsListener = do
  res <- socketConnect
  socketListen res


socketConnect :: (MonadReader r m, HasSlackConfig r, MonadIO m, MonadLogger m, MonadThrow m) => m SlackSocketConnectResp
socketConnect = do
  config <- askSlackConfig
  $(logInfo) "Obtaining a websocket url."
  let opts = defaults & header "Authorization" .~ ["Bearer " <> config ^. slackAppToken]
  res <- liftIO $ postWith opts "https://slack.com/api/apps.connections.open" ([] :: [FormParam])
  let eitherBody = eitherDecode' $ res ^. responseBody
  case eitherBody of Left err -> throwString err
                     Right body -> return body


socketListen :: (MonadReader r m, HasConfig r, MonadIO m, MonadBaseControl IO m, MonadLogger m, Forall (Pure m), MonadCatch m) =>
                SlackSocketConnectResp ->
                m ()
socketListen connectResp = do
  let eitherUriAuthority = do
        uri <- maybe (fail "Could not parse websockets url.") return $ parseAbsoluteURI $ connectResp ^. sscr_url
        authority' <- maybe (fail "Could not parse websockets domain.") return $ uriAuthority uri
        return (uri, authority')
  (uri, authority') <- either throwString return eitherUriAuthority
  let domain = uriRegName authority'
      path' = uriPath uri <> uriQuery uri
  nameCache <- newCache
  liftBaseOp (runSecureClient domain 443 path') $ \connection -> do
    $(logInfo) "Listening to the slack websocket."
    queue <- liftIO $ newTBQueueIO 100
    let queueEvent event = liftIO $ atomically (writeTBQueue queue event)
    let readLoop = do
          handleAny loopErrorHandler $ do
            raw <- liftIO $ receiveData connection
            envelope <- either throwString return (eitherDecodeStrict' raw)
            mapM_ (\eid -> liftIO $ sendTextData connection $ encode $ SlackSocketAck eid) (envelope ^. sse_envelope_id)
            when (envelope ^. sse_type == "disconnect") $ throw ConnectionClosed
            mapM_ (queueEvent . (^. ssp_event)) (envelope ^. sse_payload)
          readLoop
    let writeLoop = do
          handleAny loopErrorHandler $ do
            event <- liftIO (atomically $ readTBQueue queue)
            mRes <- mBuildResponse nameCache event
            mapM_ sendMessage mRes
          writeLoop
    race_ readLoop writeLoop

loopErrorHandler :: (MonadLogger m, MonadThrow m)
                 => SomeException
                 -> m ()
loopErrorHandler e = do
  when (connectionClosed e) $ throw ConnectionClosed
  $(logError) $ tshow e
    where mConnectionExc = fromException :: SomeException -> Maybe ConnectionException
          mClosedExc ConnectionClosed = Just ConnectionClosed
          mClosedExc _ = Nothing
          connectionClosed e = isJust (join . fmap mClosedExc . mConnectionExc $ e)



mBuildResponse :: (MonadReader r m, HasConfig r, MonadIO m, MonadLogger m, MonadBaseControl IO m, Forall (Pure m), MonadThrow m)
               => NameCache
               -> SlackEvent
               -> m (Maybe GroupMeBotMessage)
mBuildResponse cache event = case event of (SlackEventOther val) -> return Nothing
                                           (SlackEventMessage message) -> handleMessage message
                                           (SlackEventFileShare fileShare) -> handleFileShare fileShare
  where
    getCorrectChannel config_ = config_ ^. configSlack . slackChannelId
    getName userId = liftIO $ lookupECM cache userId
    handleMessage message = do
      config_ <- askConfig
      if getCorrectChannel config_ /= message ^. sm_channel
      then return Nothing
      else do
        let gmConfig = config_ ^. groupMeConfig
        userName <- getName $ message ^. sm_user
        let botId = gmConfig ^. configGroupMeBotId
        return $ Just $ GroupMeBotMessage
                          (gmConfig ^. configGroupMeBotId)
                          (userName <> ": " <> message ^. sm_text)
                          (gmConfig ^. configGroupMeAccessKey)
                          Nothing
    handleFileShare fileShare = do
      config_ <- askConfig
      if getCorrectChannel config_ /= fileShare ^. sfs_channel
      then return Nothing
      else do
        let gmConfig = config_ ^. configGroupMe
            userId = fileShare ^. sfs_user
            slackFile = fileShare ^. sfs_file
        (gmPictureUrl, userName) <- concurrently (transferSlackImageToGroupMe slackFile) (getName userId)
        let fileComment = case fileShare ^. sfs_file . sf_initial_comment of
                            Nothing -> userName <> ": "
                            Just comment -> userName <> ": " <> comment ^. sfc_comment
        return $ Just $ GroupMeBotMessage
                          (gmConfig ^. configGroupMeBotId)
                          fileComment
                          (gmConfig ^. configGroupMeAccessKey)
                          (Just gmPictureUrl)

transferSlackImageToGroupMe :: (MonadReader r m, HasConfig r, MonadIO m, MonadLogger m, MonadThrow m) => SlackFile -> m Text
transferSlackImageToGroupMe slackFile = do
  fileData <- getFile $ slackFile ^. sf_url_private
  gmUploadRes <- uploadPicture (slackFile ^. sf_name) fileData
  return $ gmUploadRes ^. gmur_url

type NameCache = ECM IO MVar () HashMap Text Text

newCache :: (MonadReader r m, HasSlackConfig r, MonadIO m) => m NameCache
newCache = do
  config <- askSlackConfig
  let cacheAccess = consistentDuration 100 $ \state userId -> do
                                                userName <- getUserName config userId
                                                return (state, userName)
      cacheTick = do
        time <- getPOSIXTime
        return $ round (time * 100)
      cacheFreq = 1
      cacheLRU = CacheWithLRUList 100 100 200
  liftIO $ newECMIO cacheAccess cacheTick cacheFreq cacheLRU
