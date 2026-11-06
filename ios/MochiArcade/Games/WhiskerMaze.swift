// WHISKER MAZE - placeholder until the full game lands (port of mochi_arcade/games/whisker_maze.py).
import Foundation

final class WhiskerMaze: GameScene {
    /// Touch lines replacing the first `helpSkip` desktop lines of the how-to text.
    static let touchHelp = ["PAD  MOVE", "A    ACTION"]
    static let helpSkip = 2
    override var music: String? { "title" }

    override func tick(_ dt: Double) { if t > 2.5 { endGame(false, "COMING SOON") } }
    override func render(_ s: Surface) { WhiskerMaze.preview(s, t) }

    static func preview(_ s: Surface, _ t: Double) {
        s.fill(col("night"))
        drawText(s, "WHISKER MAZE", s.w / 2, s.h / 2 - 8, "yellow", align: .center)
        drawText(s, "COMING SOON", s.w / 2, s.h / 2 + 4, "white", align: .center)
    }
}
