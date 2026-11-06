// Player profiles with settings, high scores and per-game options (port of mochi_arcade/profiles.py).
import Foundation

struct Settings: Codable {
    var music = 6
    var sfx = 8
    var scanlines = false
    var shake = true
    var haptics = true
    var controls = 6 // touch-control opacity 2..10
    var screen = "full" // full: as big as the screen allows | stretch: fill the whole screen | pixel: integer scale

    init() {}

    // decode field by field so profiles saved by older builds (missing keys) still load
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        music = try c.decodeIfPresent(Int.self, forKey: .music) ?? music
        sfx = try c.decodeIfPresent(Int.self, forKey: .sfx) ?? sfx
        scanlines = try c.decodeIfPresent(Bool.self, forKey: .scanlines) ?? scanlines
        shake = try c.decodeIfPresent(Bool.self, forKey: .shake) ?? shake
        haptics = try c.decodeIfPresent(Bool.self, forKey: .haptics) ?? haptics
        controls = try c.decodeIfPresent(Int.self, forKey: .controls) ?? controls
        screen = try c.decodeIfPresent(String.self, forKey: .screen) ?? screen
    }
}

struct ScoreEntry: Codable, Equatable {
    var score: Int
    var when: Double
    var detail: String
}

struct GameRecord: Codable {
    var best = 0
    var plays = 0
    var top: [ScoreEntry] = []
    var options: [String: String] = [:]
}

final class Profile: Codable {
    var name: String
    var avatar: String
    var created: Double
    var settings = Settings()
    var games: [String: GameRecord] = [:]

    init(name: String, avatar: String) {
        self.name = name
        self.avatar = avatar
        created = Date().timeIntervalSince1970
    }
}

let AVATARS = ["white", "pink", "peach", "mint", "sky", "lavender", "yellow", "lime"]
let MAX_PROFILES = 8
let MAX_NAME = 8

final class Store {
    struct Data_: Codable { var last: String?; var profiles: [Profile] }
    private(set) var data = Data_(last: nil, profiles: [])
    private let url: URL

    init() {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MochiArcade", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        url = dir.appendingPathComponent("profiles.json")
        if let d = try? Data(contentsOf: url), let v = try? JSONDecoder().decode(Data_.self, from: d) { data = v }
    }

    var profiles: [Profile] { data.profiles }

    func save() {
        if let d = try? JSONEncoder().encode(data) { try? d.write(to: url, options: .atomic) }
    }

    func get(_ name: String?) -> Profile? { profiles.first { $0.name == name } }
    func last() -> Profile? { get(data.last) ?? profiles.first }

    func create(_ name: String, avatar: String) -> Profile? {
        let n = String(name.trimmingCharacters(in: .whitespaces).uppercased().prefix(MAX_NAME))
        if n.isEmpty || get(n) != nil || profiles.count >= MAX_PROFILES { return nil }
        let p = Profile(name: n, avatar: avatar)
        data.profiles.append(p)
        data.last = n
        save()
        return p
    }

    func delete(_ name: String) {
        data.profiles.removeAll { $0.name == name }
        if data.last == name { data.last = nil }
        save()
    }

    func select(_ p: Profile) { data.last = p.name; save() }

    func game(_ p: Profile, _ gid: String) -> GameRecord { p.games[gid] ?? GameRecord() }

    func setOptions(_ p: Profile, _ gid: String, _ opts: [String: String]) {
        var g = game(p, gid)
        g.options = opts
        p.games[gid] = g
        save()
    }

    /// Store a finished game; returns (newBest, rank).
    func record(_ p: Profile, _ gid: String, _ score: Int, _ detail: String) -> (Bool, Int?) {
        var g = game(p, gid)
        g.plays += 1
        let newBest = score > g.best
        g.best = max(g.best, score)
        let e = ScoreEntry(score: score, when: Date().timeIntervalSince1970, detail: detail)
        g.top.append(e)
        g.top.sort { $0.score > $1.score }
        g.top = Array(g.top.prefix(10))
        let rank = g.top.firstIndex(of: e).map { $0 + 1 }
        p.games[gid] = g
        save()
        return (newBest, rank)
    }
}
