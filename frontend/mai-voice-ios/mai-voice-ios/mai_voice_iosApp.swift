//
//  mai_voice_iosApp.swift
//  mai-voice-ios
//
//  Created by Bibuti Koley on 14/09/26.
//

import SwiftUI

@main
struct mai_voice_iosApp: App {
    @StateObject private var model = VoiceAgentModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
        }
    }
}
