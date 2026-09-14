//
//  VoiceAgentModel.swift
//  mai-voice-ios
//
//  Wraps the Pipecat iOS client (SmallWebRTC transport) and publishes UI state.
//

import Combine
import Foundation
import PipecatClientIOS
import PipecatClientIOSSmallWebrtc

enum ConnectionStatus {
    case idle
    case connecting
    case connected
    case disconnecting
}

struct TranscriptEntry: Identifiable {
    let id = UUID()
    let isUser: Bool
    let text: String
}

@MainActor
final class VoiceAgentModel: NSObject, ObservableObject, PipecatClientDelegate {

    static let defaultServerURL = "http://localhost:7860"

    private static let serverURLKey = "server_url"

    @Published var status: ConnectionStatus = .idle
    @Published var botReady = false
    @Published var micEnabled = true
    @Published var botSpeaking = false
    @Published var userSpeaking = false
    @Published var userLevel: Float = 0
    @Published var botLevel: Float = 0
    @Published var liveBotText = ""
    @Published var transcripts: [TranscriptEntry] = []
    @Published var errorMessage: String?
    @Published var serverURL: String

    private var client: PipecatClient?

    override init() {
        let stored = UserDefaults.standard.string(forKey: Self.serverURLKey)
        self.serverURL = stored ?? Self.defaultServerURL
        super.init()

        // Dev/testing affordance: connect as soon as the app launches.
        if ProcessInfo.processInfo.arguments.contains("--auto-connect") {
            DispatchQueue.main.async { [weak self] in
                self?.connect()
            }
        }
    }

    func saveServerURL(_ value: String) {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let resolved = trimmed.isEmpty ? Self.defaultServerURL : trimmed
        serverURL = resolved
        UserDefaults.standard.set(resolved, forKey: Self.serverURLKey)
    }

    func connect() {
        guard client == nil else { return }

        let base = serverURL.trimmingCharacters(in: .whitespacesAndNewlines)
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let endpoint = URL(string: "\(base)/start") else {
            errorMessage = "Invalid server URL: \(serverURL)"
            return
        }

        status = .connecting
        errorMessage = nil
        transcripts = []
        liveBotText = ""
        micEnabled = true

        let transport = SmallWebRTCTransport()
        let options = PipecatClientOptions(transport: transport, enableMic: true, enableCam: false)
        let newClient = PipecatClient(options: options)
        newClient.delegate = self
        client = newClient

        let request = APIRequest(
            endpoint: endpoint,
            requestData: .object(["transport": .string("webrtc")])
        )

        newClient.startBotAndConnect(startBotParams: request) { [weak self] (result: Result<SmallWebRTCStartBotResult, AsyncExecutionError>) in
            guard case .failure(let error) = result else { return }
            Task { @MainActor [weak self] in
                self?.fail("Could not start the bot: \(error.localizedDescription)")
            }
        }
    }

    func disconnect() {
        guard let client else { return }
        status = .disconnecting
        client.disconnect { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.releaseClient()
            }
        }
    }

    func toggleMic() {
        guard let client else { return }
        let enabled = !micEnabled
        client.enableMic(enable: enabled) { [weak self] result in
            guard case .success = result else { return }
            Task { @MainActor [weak self] in
                self?.micEnabled = enabled
            }
        }
    }

    func dismissError() {
        errorMessage = nil
    }

    // MARK: - Internals

    private func fail(_ message: String) {
        errorMessage = message
        releaseClient()
    }

    private func releaseClient() {
        client?.release()
        client = nil
        status = .idle
        botReady = false
        userSpeaking = false
        botSpeaking = false
        userLevel = 0
        botLevel = 0
        liveBotText = ""
    }

    private func appendTranscript(isUser: Bool, text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        transcripts.append(TranscriptEntry(isUser: isUser, text: trimmed))
    }

    // MARK: - PipecatClientDelegate

    func onConnected() {
        status = .connected
    }

    func onDisconnected() {
        releaseClient()
    }

    func onError(message: RTVIMessageInbound) {
        fail("Backend error: \(message)")
    }

    func onBotReady(botReadyData: BotReadyData) {
        botReady = true
    }

    func onUserStartedSpeaking() {
        userSpeaking = true
    }

    func onUserStoppedSpeaking() {
        userSpeaking = false
        userLevel = 0
    }

    func onBotStartedSpeaking() {
        botSpeaking = true
    }

    func onBotStoppedSpeaking() {
        let text = liveBotText.trimmingCharacters(in: .whitespacesAndNewlines)
        botSpeaking = false
        botLevel = 0
        liveBotText = ""
        if !text.isEmpty {
            transcripts.append(TranscriptEntry(isUser: false, text: text))
        }
    }

    func onLocalAudioLevel(level: Float) {
        userLevel = level
    }

    func onRemoteAudioLevel(level: Float, participant: Participant) {
        botLevel = level
    }

    func onUserTranscript(data: Transcript) {
        if data.final == true {
            appendTranscript(isUser: true, text: data.text)
        }
    }

    func onBotLlmText(data: BotLLMText) {
        liveBotText += data.text
    }
}
