package io.bibuti.maivoiceandroid.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import io.bibuti.maivoiceandroid.voice.ConnectionStatus
import io.bibuti.maivoiceandroid.voice.TranscriptEntry
import io.bibuti.maivoiceandroid.voice.TranscriptRole
import io.bibuti.maivoiceandroid.voice.VoiceUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VoiceScreen(
    state: VoiceUiState,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit,
    onToggleMic: () -> Unit,
    onOpenSettings: () -> Unit,
    onDismissError: () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("mai voice") },
                actions = {
                    TextButton(onClick = onOpenSettings) { Text("Settings") }
                },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            state.error?.let { message ->
                ErrorBanner(message = message, onDismiss = onDismissError)
                Spacer(Modifier.height(8.dp))
            }

            Spacer(Modifier.height(12.dp))

            VoiceOrb(
                state = state,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(220.dp),
            )

            Text(
                text = statusText(state),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            Text(
                text = state.serverUrl,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 4.dp),
            )

            Spacer(Modifier.height(16.dp))

            TranscriptList(
                entries = state.transcripts,
                liveBotText = state.liveBotText,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            )

            Spacer(Modifier.height(12.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                val connected = state.status == ConnectionStatus.Connected ||
                    state.status == ConnectionStatus.Connecting

                FilledTonalButton(
                    onClick = onToggleMic,
                    enabled = state.status == ConnectionStatus.Connected,
                    modifier = Modifier.weight(1f),
                ) {
                    Text(if (state.micEnabled) "Mute" else "Unmute")
                }

                Button(
                    onClick = { if (state.status == ConnectionStatus.Connected) onDisconnect() else onConnect() },
                    enabled = state.status != ConnectionStatus.Connecting &&
                        state.status != ConnectionStatus.Disconnecting,
                    modifier = Modifier.weight(1f),
                ) {
                    Text(
                        when {
                            state.status == ConnectionStatus.Connecting -> "Connecting…"
                            connected -> "Disconnect"
                            else -> "Connect"
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun ErrorBanner(message: String, onDismiss: () -> Unit) {
    Surface(
        color = MaterialTheme.colorScheme.errorContainer,
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = message,
                color = MaterialTheme.colorScheme.onErrorContainer,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = onDismiss) { Text("Dismiss") }
        }
    }
}

@Composable
private fun VoiceOrb(state: VoiceUiState, modifier: Modifier = Modifier) {
    val active = state.status == ConnectionStatus.Connected
    val level = when {
        state.botSpeaking -> maxOf(0.4f, state.botAudioLevel)
        state.userSpeaking -> maxOf(0.3f, state.userAudioLevel)
        active -> 0.18f
        else -> 0.08f
    }
    val animatedLevel by animateFloatAsState(
        targetValue = level.coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 120),
        label = "orbLevel",
    )

    val targetColor = when {
        state.status == ConnectionStatus.Error -> MaterialTheme.colorScheme.error
        state.botSpeaking -> MaterialTheme.colorScheme.primary
        state.userSpeaking -> MaterialTheme.colorScheme.tertiary
        active -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.surfaceVariant
    }
    val orbColor by animateColorAsState(targetValue = targetColor, label = "orbColor")

    val infinite = rememberInfiniteTransition(label = "orbPulse")
    val pulse by infinite.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.06f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "orbPulse",
    )

    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Canvas(modifier = Modifier.size(220.dp)) {
            val base = size.minDimension / 2f
            val radius = base * (0.45f + 0.5f * animatedLevel) * (if (active) pulse else 1f)

            drawCircle(color = orbColor.copy(alpha = 0.10f), radius = radius * 1.18f)
            drawCircle(color = orbColor.copy(alpha = 0.18f), radius = radius * 1.08f)
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        orbColor.copy(alpha = 0.95f),
                        orbColor.copy(alpha = 0.45f),
                    ),
                ),
                radius = radius,
            )
        }
    }
}

@Composable
private fun TranscriptList(
    entries: List<TranscriptEntry>,
    liveBotText: String,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()

    LaunchedEffect(entries.size, liveBotText) {
        val total = entries.size + if (liveBotText.isNotBlank()) 1 else 0
        if (total > 0) listState.animateScrollToItem(total - 1)
    }

    LazyColumn(
        state = listState,
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (entries.isEmpty() && liveBotText.isBlank()) {
            item {
                Text(
                    text = "Connect and start talking — your conversation will appear here.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.outline,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 24.dp),
                )
            }
        }

        items(entries, key = { it.id }) { entry ->
            TranscriptBubble(text = entry.text, isUser = entry.role == TranscriptRole.User)
        }

        if (liveBotText.isNotBlank()) {
            item {
                TranscriptBubble(text = liveBotText, isUser = false, live = true)
            }
        }
    }
}

@Composable
private fun TranscriptBubble(text: String, isUser: Boolean, live: Boolean = false) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        Surface(
            color = if (isUser) MaterialTheme.colorScheme.surfaceVariant
            else MaterialTheme.colorScheme.primaryContainer,
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier.fillMaxWidth(0.85f),
        ) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                Text(
                    text = if (isUser) "You" else "Bot",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text = text,
                    style = MaterialTheme.typography.bodyMedium,
                    fontStyle = if (live) FontStyle.Italic else FontStyle.Normal,
                    color = if (isUser) MaterialTheme.colorScheme.onSurfaceVariant
                    else MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
        }
    }
}

private fun statusText(state: VoiceUiState): String = when {
    state.status == ConnectionStatus.Connecting -> "Connecting…"
    state.status == ConnectionStatus.Disconnecting -> "Disconnecting…"
    state.status == ConnectionStatus.Error -> "Connection error"
    state.status == ConnectionStatus.Connected && !state.botReady -> "Waiting for bot…"
    state.status == ConnectionStatus.Connected && state.botSpeaking -> "Speaking…"
    state.status == ConnectionStatus.Connected && state.userSpeaking -> "Listening…"
    state.status == ConnectionStatus.Connected -> "Connected"
    else -> "Disconnected"
}
