// Chiptune synthesizer, sound effects and looping songs (port of mochi_arcade/audio.py).
import AVFoundation
import Foundation

enum Synth {
    static let SR = 22050
    private static let noteOffset: [String: Int] = ["C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2,
                                                    "G#": -1, "A": 0, "A#": 1, "B": 2]

    static func freq(_ note: String) -> Double {
        let name = String(note.dropLast()), octave = Int(String(note.last!)) ?? 4
        return 440.0 * pow(2.0, Double((noteOffset[name] ?? 0) + (octave - 4) * 12) / 12.0)
    }

    static func voice(_ kind: String, _ f0: Double, _ n: Int, _ vol: Double, f1: Double? = nil, duty: Double = 0.25,
                      attack: Double = 0.004, release: Double = 0.03, decay: Double = 0.35, vibrato: Double = 0) -> [Float] {
        if n <= 0 { return [] }
        var out = [Float](repeating: 0, count: n)
        let att = max(1, Int(attack * Double(SR)))
        let rel = max(1, min(n, Int(release * Double(SR))))
        var ph = 0.0, nv = 0.0
        var hold = 0
        for i in 0 ..< n {
            let t = Double(i) / Double(n)
            var f = f1 == nil ? f0 : f0 + (f1! - f0) * t
            if vibrato != 0 { f *= 1 + vibrato * sin(Double(i) * 0.0025) }
            ph += f / Double(SR)
            if ph >= 1 { ph -= floor(ph) }
            var s: Double
            switch kind {
            case "square": s = ph < duty ? 1 : -1
            case "triangle": s = ph < 0.5 ? 4 * ph - 1 : 3 - 4 * ph
            case "sine": s = sin(ph * 2 * .pi)
            default:
                if hold <= 0 { nv = Double.random(in: -1 ... 1); hold = max(1, Int(Double(SR) / max(f, 1))) }
                hold -= 1
                s = nv
            }
            var env = 1 - decay * t
            if i < att { env *= Double(i) / Double(att) }
            if i >= n - rel { env *= Double(n - i) / Double(rel) }
            out[i] = Float(s * vol * env)
        }
        return out
    }

    static func n(_ seconds: Double) -> Int { Int(seconds * Double(SR)) }

    static func arp(_ notes: [String], _ d: Double, wave: String = "square", vol: Double = 0.35, duty: Double = 0.25) -> [Float] {
        notes.flatMap { voice(wave, freq($0), n(d), vol, duty: duty, release: 0.01, decay: 0.2) }
    }

    static let sfx: [String: () -> [Float]] = [
        "move": { voice("square", 880, n(0.03), 0.25, duty: 0.125, decay: 0.5) },
        "select": { arp(["E5", "B5"], 0.05) },
        "back": { arp(["B5", "E5"], 0.05) },
        "type": { voice("square", 1200, n(0.02), 0.2, duty: 0.5) },
        "jump": { voice("square", 280, n(0.13), 0.3, f1: 720, duty: 0.25) },
        "bubble": { voice("sine", 520, n(0.16), 0.45, f1: 980, vibrato: 0.05) },
        "trap": { voice("sine", 980, n(0.22), 0.45, f1: 380) },
        "pop": { voice("noise", 4000, n(0.04), 0.35) + voice("square", 1300, n(0.05), 0.3, duty: 0.5) },
        "fruit": { arp(["B5", "E6"], 0.07, vol: 0.3) },
        "hurt": { voice("square", 620, n(0.32), 0.35, f1: 140, duty: 0.5) },
        "die": { arp(["G5", "E5", "C5", "G4", "C4"], 0.09, vol: 0.32, duty: 0.5) },
        "shoot": { voice("square", 1500, n(0.08), 0.22, f1: 600, duty: 0.125) },
        "explode": { voice("noise", 2200, n(0.3), 0.45, f1: 300, decay: 0.9) },
        "boom": { voice("noise", 900, n(0.6), 0.55, f1: 80, decay: 0.95) },
        "rotate": { voice("square", 520, n(0.03), 0.2, duty: 0.5) },
        "lock": { voice("triangle", 170, n(0.06), 0.5) },
        "line": { arp(["C6", "E6", "G6"], 0.045, vol: 0.3) },
        "quad": { arp(["C5", "E5", "G5", "C6", "E6", "G6", "C7"], 0.05, vol: 0.3) },
        "levelup": { arp(["G5", "C6", "E6", "G6"], 0.07, vol: 0.3, duty: 0.5) },
        "eat": { voice("square", 700, n(0.05), 0.3, f1: 1100, duty: 0.25) },
        "bonus": { arp(["E6", "G6", "B6", "E7"], 0.04, vol: 0.25) },
        "paddle": { voice("square", 440, n(0.04), 0.3, duty: 0.5) },
        "brick": { voice("square", 880, n(0.04), 0.28, duty: 0.25) },
        "tin": { voice("triangle", 1700, n(0.04), 0.4) },
        "powerup": { voice("square", 300, n(0.25), 0.3, f1: 1200, duty: 0.5, vibrato: 0.08) },
        "extra": { arp(["C6", "E6", "G6", "C7", "G6", "C7"], 0.06, vol: 0.3, duty: 0.5) },
        "hold": { voice("triangle", 660, n(0.05), 0.4, f1: 880) },
        "gameover": { arp(["C5", "B4", "A#4", "A4"], 0.22, vol: 0.3, duty: 0.5) },
        "win": { arp(["C5", "E5", "G5", "C6", "G5", "C6", "E6"], 0.08, vol: 0.3, duty: 0.5) },
        // arcade kit (Arcade.swift)
        "combo": { arp(["C6", "G6"], 0.04, vol: 0.28) },
        "fever": { arp(["C5", "E5", "G5", "C6", "E6", "G6", "C7", "E7"], 0.035, vol: 0.3, duty: 0.5) },
        "jackpot": { arp(["G5", "C6", "E6", "G6", "C7", "E7", "G7", "C7", "E7", "G7"], 0.05, vol: 0.3, duty: 0.5) },
        "card": { voice("square", 660, n(0.08), 0.3, f1: 1320, duty: 0.5) },
        "coin": { voice("square", 988, n(0.05), 0.25, duty: 0.5) + voice("square", 1319, n(0.12), 0.25, duty: 0.5) },
        "warning": { (0 ..< 3).flatMap { _ in voice("square", 440, n(0.14), 0.3, f1: 880, duty: 0.5) } },
        "bossdown": { voice("noise", 1800, n(1.0), 0.55, f1: 60, decay: 0.97) },
        "stage": { arp(["C5", "G5", "C6"], 0.07, vol: 0.3, duty: 0.5) },
    ]

    private static func drum(_ kind: String, _ n: Int) -> [Float] {
        switch kind {
        case "K": return voice("sine", 160, n, 0.9, f1: 45, release: 0.02, decay: 0.9)
        case "S":
            let a = voice("noise", 6000, n, 0.35, decay: 0.95), b = voice("triangle", 210, n, 0.25, decay: 1.0)
            return zip(a, b).map { $0 + $1 }
        default:
            let h = min(n, Int(0.03 * Double(SR)))
            return voice("noise", 9000, h, 0.18, decay: 1.0) + [Float](repeating: 0, count: max(0, n - h))
        }
    }

    static func renderSong(_ song: GData.Song) -> [Float] {
        let beat = 60.0 / song.bpm
        var tracks: [[Float]] = []
        for ch in song.channels {
            var out: [Float] = []
            for tok in ch.notes.split(separator: " ") {
                let parts = tok.split(separator: ":")
                let name = String(parts[0])
                var den = String(parts[1])
                let dotted = den.hasSuffix(".")
                if dotted { den.removeLast() }
                let beats = 4.0 / (Double(den) ?? 4) * (dotted ? 1.5 : 1)
                let count = Int(beats * beat * Double(SR))
                if name == "R" {
                    out += [Float](repeating: 0, count: count)
                } else if ch.wave == "drums" {
                    let d = drum(name, min(count, Int(0.18 * Double(SR))))
                    out += d + [Float](repeating: 0, count: max(0, count - d.count))
                } else {
                    let on = Int(Double(count) * ch.gate)
                    out += voice(ch.wave, freq(name), on, ch.vol, duty: ch.duty, decay: ch.decay, vibrato: ch.vibrato)
                    out += [Float](repeating: 0, count: count - on)
                }
            }
            tracks.append(out)
        }
        let len = tracks.map { $0.count }.max() ?? 0
        var mix = [Float](repeating: 0, count: len)
        for t in tracks { for i in 0 ..< t.count { mix[i] += t[i] } }
        let g = Float(song.gain)
        return mix.map { $0 * g }
    }

    /// 16-bit mono WAV in memory.
    static func wav(_ samples: [Float]) -> Data {
        var d = Data()
        func u32(_ v: UInt32) { var x = v.littleEndian; withUnsafeBytes(of: &x) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { var x = v.littleEndian; withUnsafeBytes(of: &x) { d.append(contentsOf: $0) } }
        let bytes = UInt32(samples.count * 2)
        d.append(contentsOf: Array("RIFF".utf8)); u32(36 + bytes); d.append(contentsOf: Array("WAVE".utf8))
        d.append(contentsOf: Array("fmt ".utf8)); u32(16); u16(1); u16(1); u32(UInt32(SR)); u32(UInt32(SR * 2)); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(bytes)
        var pcm = [Int16](repeating: 0, count: samples.count)
        for i in 0 ..< samples.count { pcm[i] = Int16(max(-1, min(1, samples[i])) * 32767) }
        pcm.withUnsafeBytes { d.append(contentsOf: $0) }
        return d
    }
}

final class Audio {
    private var pools: [String: [AVAudioPlayer]] = [:]
    private var songData: [String: Data] = [:]
    private var musicPlayer: AVAudioPlayer?
    private(set) var current: String?
    var sfxVol: Float = 0.8
    var musicVol: Float = 0.6

    init() {
        #if os(iOS)
        try? AVAudioSession.sharedInstance().setCategory(.ambient, options: [.mixWithOthers])
        try? AVAudioSession.sharedInstance().setActive(true)
        #endif
        for (name, gen) in Synth.sfx {
            let data = Synth.wav(gen())
            pools[name] = (0 ..< 3).compactMap { _ in
                let p = try? AVAudioPlayer(data: data)
                p?.prepareToPlay()
                return p
            }
        }
        // render the songs in the background so the first menu does not hitch
        DispatchQueue.global(qos: .utility).async {
            var rendered: [String: Data] = [:]
            for (name, song) in GData.songs { rendered[name] = Synth.wav(Synth.renderSong(song)) }
            DispatchQueue.main.async {
                for (k, v) in rendered where self.songData[k] == nil { self.songData[k] = v }
                if let c = self.current, self.musicPlayer == nil { self.current = nil; self.music(c) }
            }
        }
    }

    func setVolumes(music: Int, sfx: Int) {
        musicVol = Float(max(0, min(10, music))) / 10
        sfxVol = Float(max(0, min(10, sfx))) / 10
        musicPlayer?.volume = musicVol * 0.7
    }

    func play(_ name: String) {
        guard sfxVol > 0, let pool = pools[name] else { return }
        let p = pool.first { !$0.isPlaying } ?? pool.first
        p?.currentTime = 0
        p?.volume = sfxVol
        p?.play()
    }

    func music(_ name: String?) {
        if name == current && (musicPlayer != nil || name == nil) { return }
        current = name
        guard let name = name else { musicPlayer?.setVolume(0, fadeDuration: 0.3); musicPlayer = nil; return }
        guard let data = songData[name] else { musicPlayer?.stop(); musicPlayer = nil; return } // starts when rendered
        musicPlayer?.stop()
        musicPlayer = try? AVAudioPlayer(data: data)
        musicPlayer?.numberOfLoops = -1
        musicPlayer?.volume = musicVol * 0.7
        musicPlayer?.play()
    }

    func stopMusic() { music(nil) }
    func pauseMusic() { musicPlayer?.pause() }
    func resumeMusic() { musicPlayer?.play() }
}
