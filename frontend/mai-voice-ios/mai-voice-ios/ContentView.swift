//
//  ContentView.swift
//  mai-voice-ios
//

import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: VoiceAgentModel
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            VoiceView(showSettings: $showSettings)
                .navigationTitle("mai voice")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Settings") { showSettings = true }
                    }
                }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView()
                .environmentObject(model)
        }
    }
}

// MARK: - Voice screen

private struct VoiceView: View {
    @EnvironmentObject private var model: VoiceAgentModel
    @Binding var showSettings: Bool

    var body: some View {
        VStack(spacing: 12) {
            if let error = model.errorMessage {
                ErrorBanner(message: error) { model.dismissError() }
            }

            VoiceOrb()
                .frame(height: 220)

            Text(statusText)
                .font(.headline)
                .foregroundStyle(.secondary)

            Text(model.serverURL)
                .font(.caption)
                .foregroundStyle(.tertiary)

            TranscriptList()
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            HStack(spacing: 12) {
                Button(model.micEnabled ? "Mute" : "Unmute") {
                    model.toggleMic()
                }
                .buttonStyle(.bordered)
                .frame(maxWidth: .infinity)
                .disabled(model.status != .connected)

                Button(model.status == .connected ? "Disconnect" : "Connect") {
                    if model.status == .connected {
                        model.disconnect()
                    } else {
                        model.connect()
                    }
                }
                .buttonStyle(.borderedProminent)
                .frame(maxWidth: .infinity)
                .disabled(model.status == .connecting || model.status == .disconnecting)
            }
            .padding(.bottom, 8)
        }
        .padding(.horizontal, 20)
    }

    private var statusText: String {
        switch model.status {
        case .connecting: return "Connecting…"
        case .disconnecting: return "Disconnecting…"
        case .connected:
            if !model.botReady { return "Waiting for bot…" }
            if model.botSpeaking { return "Speaking…" }
            if model.userSpeaking { return "Listening…" }
            return "Connected"
        case .idle:
            return model.errorMessage == nil ? "Disconnected" : "Connection error"
        }
    }
}

// MARK: - Orb

private struct VoiceOrb: View {
    @EnvironmentObject private var model: VoiceAgentModel

    var body: some View {
        let active = model.status == .connected
        let target = min(max(
            model.botSpeaking ? max(0.4, model.botLevel) :
            model.userSpeaking ? max(0.3, model.userLevel) :
            active ? 0.18 : 0.08,
            0, 1
        ), 1)

        TimelineView(.animation(minimumInterval: 1.0 / 30.0)) { context in
            let time = context.date.timeIntervalSinceReferenceDate
            let pulse = active ? 1.0 + 0.05 * sin(time * 4) : 1.0
            let level = CGFloat(target)
            let radius = 100 * (0.45 + 0.5 * level) * pulse

            ZStack {
                Circle()
                    .fill(orbColor(active: active).opacity(0.10))
                    .frame(width: radius * 2.3, height: radius * 2.3)
                Circle()
                    .fill(orbColor(active: active).opacity(0.18))
                    .frame(width: radius * 2.1, height: radius * 2.1)
                Circle()
                    .fill(
                        RadialGradient(
                            colors: [orbColor(active: active).opacity(0.95),
                                     orbColor(active: active).opacity(0.45)],
                            center: .center,
                            startRadius: 0,
                            endRadius: radius
                        )
                    )
                    .frame(width: radius * 2, height: radius * 2)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .animation(.easeOut(duration: 0.12), value: target)
        }
    }

    private func orbColor(active: Bool) -> Color {
        if model.botSpeaking { return .accentColor }
        if model.userSpeaking { return .teal }
        return active ? .accentColor : Color(.systemGray4)
    }
}

// MARK: - Transcripts

private struct TranscriptList: View {
    @EnvironmentObject private var model: VoiceAgentModel

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 8) {
                    if model.transcripts.isEmpty && model.liveBotText.isEmpty {
                        Text("Connect and start talking — your conversation will appear here.")
                            .font(.subheadline)
                            .foregroundStyle(.tertiary)
                            .multilineTextAlignment(.center)
                            .padding(.top, 24)
                            .id("empty")
                    }

                    ForEach(model.transcripts) { entry in
                        TranscriptBubble(text: entry.text, isUser: entry.isUser)
                            .id(entry.id)
                    }

                    if !model.liveBotText.isEmpty {
                        TranscriptBubble(text: model.liveBotText, isUser: false, live: true)
                            .id("live-bot")
                    }
                }
                .padding(.vertical, 4)
            }
            .onChange(of: model.transcripts.count) { _, _ in
                withAnimation {
                    if let last = model.transcripts.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .onChange(of: model.liveBotText) { _, _ in
                withAnimation { proxy.scrollTo("live-bot", anchor: .bottom) }
            }
        }
    }
}

private struct TranscriptBubble: View {
    let text: String
    let isUser: Bool
    var live = false

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 40) }
            VStack(alignment: .leading, spacing: 2) {
                Text(isUser ? "You" : "Bot")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                Text(text)
                    .font(.subheadline)
                    .italic(live)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(isUser ? Color(.systemGray5) : Color.accentColor.opacity(0.18))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            if !isUser { Spacer(minLength: 40) }
        }
    }
}

private struct ErrorBanner: View {
    let message: String
    let onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            Text(message)
                .font(.footnote)
                .frame(maxWidth: .infinity, alignment: .leading)
            Button("Dismiss", action: onDismiss)
                .font(.footnote.bold())
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Color.red.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

// MARK: - Settings

private struct SettingsView: View {
    @EnvironmentObject private var model: VoiceAgentModel
    @Environment(\.dismiss) private var dismiss
    @State private var url: String = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Pipecat server URL") {
                    TextField("http://localhost:7860", text: $url)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                }
                Section("Audio") {
                    Toggle("Play through speaker", isOn: Binding(
                        get: { model.speakerEnabled },
                        set: { _ in model.toggleSpeaker() }
                    ))
                }
                Section {
                    Text("Simulator: http://localhost:7860\nPhysical device: your Mac's LAN IP (same Wi-Fi)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        model.saveServerURL(url)
                        dismiss()
                    }
                }
            }
            .onAppear { url = model.serverURL }
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(VoiceAgentModel())
}
