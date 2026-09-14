# Client SDK Notes

Both apps use the Pipecat client SDK with the SmallWebRTC transport and start
sessions through the runner's `/start` endpoint, exactly like the browser
client. The SDK then negotiates WebRTC against `/sessions/{id}/api/offer`.

## Android (`frontend/mai-voice-android`)

- Dependencies: `ai.pipecat:client:1.2.0`, `ai.pipecat:small-webrtc-transport:1.2.1`
  (`gradle/libs.versions.toml`).
- Permissions: `RECORD_AUDIO`, `INTERNET`, `MODIFY_AUDIO_SETTINGS`,
  `ACCESS_NETWORK_STATE`. The debug manifest enables cleartext HTTP so the
  emulator can reach `http://10.0.2.2:7860`; release builds stay HTTPS-only.
- `VoiceAgentViewModel` wraps `PipecatClientSmallWebRTC` and maps
  `PipecatEventCallbacks` to a `StateFlow<VoiceUiState>`. Connect uses:
  ```kotlin
  APIRequest(
      endpoint = "$base/start",
      requestData = Value.Object("transport" to Value.Str("webrtc")),
  )
  ```
- Transcriptions: `onUserTranscript` (final only) and `onBotLLMText` (streamed
  tokens, committed to a bubble when `onBotStoppedSpeaking` fires).
- Audio levels (`onUserAudioLevel` / `onRemoteAudioLevel`) drive the orb.
- Server URL is persisted with DataStore; default `http://10.0.2.2:7860`.
- Compose BOM note: `material-icons-*` is not bundled; use text buttons or add
  the icons artifact explicitly.
- Build: `./gradlew :app:assembleDebug`.

## iOS (`frontend/mai-voice-ios`)

- Swift packages are declared directly in `project.pbxproj`:
  `pipecat-client-ios` (product `PipecatClientIOS`) and
  `pipecat-client-ios-small-webrtc` (product `PipecatClientIOSSmallWebrtc`),
  both `upToNextMajorVersion` from `1.3.0`. The small-webrtc package pulls
  `stasel/WebRTC`.
- `Info.plist` (merged with the generated plist via `INFOPLIST_FILE`) provides
  `NSMicrophoneUsageDescription`, `NSLocalNetworkUsageDescription`, and
  `NSAllowsLocalNetworking` for HTTP to the dev server.
- The SDK is MainActor-isolated: `VoiceAgentModel` is `@MainActor` and wraps
  completion handlers in `Task { @MainActor in ... }`. Delegate callbacks
  (`PipecatClientDelegate`) run on the main actor.
- Connect uses `APIRequest(endpoint: URL("\(base)/start")!, requestData:
  .object(["transport": .string("webrtc")]))` and
  `startBotAndConnect` with `SmallWebRTCStartBotResult`.
- `--auto-connect` launch argument connects at startup (used by the E2E check).
- Server URL is persisted in `UserDefaults`; default `http://localhost:7860`.
- Build: `xcodebuild -project mai-voice-ios.xcodeproj -scheme mai-voice-ios
  -destination 'platform=iOS Simulator,name=iPhone 17' build`.

## Protocol notes

- `/start` returns `{"sessionId": ...}`; the SDK rewrites the endpoint to
  `/sessions/{sessionId}/api/offer` for the SDP exchange (PATCH sends ICE
  candidates). The development runner implements both routes.
- RTVI message types used by the UI: `user-transcript`, `bot-llm-text`,
  `bot-tts-text`, `bot-started-speaking`, `bot-stopped-speaking`, plus audio
  level events.
- Hardware AEC handles echo on real devices. On simulators/emulators the host
  mic can hear the host speakers, producing an echo loop — expected in dev.

## Verified end-to-end

- Backend: aiortc harness posting an SDP offer, sending speech, and recording the
  bot's reply; bot audio round-tripped through Qwen ASR on the host read back as
  "Hi. Stub reply. You said this is a local Qwen voice test."
- iOS simulator: connects, receives greeting, renders user/bot transcripts.
- Android emulator: same, against `10.0.2.2:7860`.
