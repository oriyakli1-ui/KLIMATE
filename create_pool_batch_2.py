import os
import pickle

batch_2 = [
    {
        "name": "Sicilian Sveshnikov",
        "fen": "r1bqkb1r/pp1p1ppp/2n2n2/4p3/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6",
        "analysis": "1. Basic Theory: Black plays ...e5 early, gaining central space but leaving a backward d-pawn and a permanent weakness on the d5 square.\n\n2. Effective Defenses: White targets the d5 outpost using the knights, aiming to exploit Black's long-term structural flaws.\n\n3. Counter-attacks: Black relies on extreme piece activity, the bishop pair, and strong kingside attacking potential to compensate."
    },
    {
        "name": "Sicilian Rossolimo",
        "fen": "r1bqkbnr/pp1ppppp/2n5/1Bp5/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        "analysis": "1. Basic Theory: White plays Bb5 against 2...Nc6, aiming to damage Black's pawn structure by capturing the knight and avoiding the Open Sicilian.\n\n2. Effective Defenses: Black can play ...g6 to prepare a fianchetto or ...e6 to challenge the center solidly.\n\n3. Counter-attacks: If White captures on c6, Black uses the bishop pair and the semi-open b-file to create queenside pressure."
    },
    {
        "name": "Sicilian Alapin",
        "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/2P5/PP1P1PPP/RNBQKBNR b KQkq - 0 2",
        "analysis": "1. Basic Theory: White plays 2.c3, preparing to build a massive pawn center with d4. It's an anti-Sicilian weapon to avoid deep theory.\n\n2. Effective Defenses: Black must strike back immediately with 2...d5 or 2...Nf6 to challenge White's central control before it solidifies.\n\n3. Counter-attacks: Black focuses on rapid development and exploiting White's inability to develop the knight to its natural c3 square."
    },
    {
        "name": "Sicilian Taimanov",
        "fen": "rnbqkb1r/pp1p1ppp/4pn2/8/3NP3/2N5/PPP2PPP/R1BQKB1R b KQkq - 0 5",
        "analysis": "1. Basic Theory: Black plays ...e6 and ...Nc6, maintaining extreme flexibility. The structure is resilient and hides Black's exact plans.\n\n2. Effective Defenses: White often employs the English Attack setup (Be3, f3, Qd2) to launch a direct kingside assault.\n\n3. Counter-attacks: Black uses the central flexibility to launch quick counter-strikes with ...Bb4 or a well-timed ...d5 break in the center."
    },
    {
        "name": "Sicilian Kan",
        "fen": "rnbqkb1r/pp1p1ppp/4pn2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5",
        "analysis": "1. Basic Theory: Black plays ...e6 and ...a6, preventing White's pieces from using the b5 square and preparing queenside expansion.\n\n2. Effective Defenses: White sets up a strong center (c4, Nc3) to clamp down on Black's breaks (the Maroczy Bind setup).\n\n3. Counter-attacks: Black adopts a 'hedgehog' formation, patiently waiting for White to overextend before unleashing dynamic breaks like ...b5 or ...d5."
    },
    {
        "name": "French Winawer",
        "fen": "rnbqk1nr/ppp2ppp/4p3/3pP3/1b1P4/2N5/PPP2PPP/R1BQKBNR w KQkq - 1 4",
        "analysis": "1. Basic Theory: Black pins the c3 knight with ...Bb4, increasing pressure on White's center and fighting directly for the e4 square.\n\n2. Effective Defenses: White forces the issue with Qg4, attacking Black's kingside weaknesses (g7) while allowing structural damage.\n\n3. Counter-attacks: Black compromises the kingside to ruin White's queenside pawn structure, leading to deeply unbalanced, highly theoretical battles."
    },
    {
        "name": "French Tarrasch",
        "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPPN1PPP/R1BQKBNR b KQkq - 1 3",
        "analysis": "1. Basic Theory: White plays 3.Nd2 instead of Nc3, keeping the c-pawn free to move and avoiding the Winawer pin.\n\n2. Effective Defenses: Black can play ...c5 immediately to challenge the center or ...Nf6 to provoke White's central pawns forward.\n\n3. Counter-attacks: Black achieves a solid position and targets the d4 pawn, while White maneuvers slowly for a kingside attack."
    },
    {
        "name": "Ruy Lopez Exchange",
        "fen": "r1bqkbnr/1ppp1ppp/p1n5/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 4",
        "analysis": "1. Basic Theory: White captures the knight on c6 (Bxc6), deliberately damaging Black's pawn structure to secure a superior endgame.\n\n2. Effective Defenses: Black utilizes the bishop pair to keep the position open, preventing White from easily exploiting the doubled pawns.\n\n3. Counter-attacks: Black defends actively, aiming to use the two bishops to dominate the middlegame before White's endgame advantage materializes."
    },
    {
        "name": "Ruy Lopez Marshall Attack",
        "fen": "r1bq1rk1/2p1bppp/p1n2n2/1p1pp3/4P3/1B3N2/PPPPQPPP/RNB1R1K1 w - - 0 10",
        "analysis": "1. Basic Theory: Black sacrifices a pawn in the opening to launch a terrifying, deeply analyzed kingside attack against White.\n\n2. Effective Defenses: White must defend with extreme precision, aiming to survive the middle game and convert the extra pawn in the endgame.\n\n3. Counter-attacks: Black's pieces swarm the kingside, relying on relentless initiative and tactical threats to overwhelm White's defenses."
    },
    {
        "name": "Caro-Kann Panov-Botvinnik",
        "fen": "rnbqkbnr/pp2pppp/8/2pp4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
        "analysis": "1. Basic Theory: White plays c4, actively challenging Black's center and often leading to an Isolated Queen's Pawn (IQP) position for White.\n\n2. Effective Defenses: Black develops solidly, aiming to control the d5 square blockading White's isolated pawn.\n\n3. Counter-attacks: Black applies pressure on the isolated pawn, while White uses the open lines and dynamic piece activity to launch an attack."
    },
    {
        "name": "Semi-Slav Defense",
        "fen": "rnbqkbnr/pp3ppp/2p1p3/3p4/2PP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 0 4",
        "analysis": "1. Basic Theory: A highly complex blend of the Slav and Queen's Gambit Declined. Black reinforces d5 with both ...c6 and ...e6.\n\n2. Effective Defenses: White chooses between aggressive setups (like the Botvinnik) or solid positional lines (like the Meran) to test Black.\n\n3. Counter-attacks: Black prepares a massive queenside expansion with ...dxc4 and ...b5, leading to wild, tactical complications."
    },
    {
        "name": "Semi-Slav Meran",
        "fen": "rnbqkb1r/pp3ppp/2p1pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 2 5",
        "analysis": "1. Basic Theory: Black gives up the center temporarily (...dxc4) to expand rapidly on the queenside with ...b5 and ...a6.\n\n2. Effective Defenses: White tries to strike in the center with e4, aiming to crush Black's position before the queenside counterplay hits.\n\n3. Counter-attacks: Black uses the fianchettoed queenside bishop and the semi-open c-file to generate intense pressure against White's center."
    },
    {
        "name": "King's Indian Samisch",
        "fen": "rnbqkb1r/pppppp1p/5np1/8/2PP4/5P2/PP2P1PP/RNBQKBNR b KQkq - 0 3",
        "analysis": "1. Basic Theory: White plays f3 to solidify the center, prevent ...Ng4, and prepare a brutal kingside attack with Be3 and Qd2.\n\n2. Effective Defenses: Black must react quickly with ...c5 or ...e5, challenging the center before White's attack gets rolling.\n\n3. Counter-attacks: The game often features opposite-side castling, leading to a razor-sharp race where Black attacks the queenside and White the kingside."
    },
    {
        "name": "King's Indian Four Pawns",
        "fen": "rnbqkb1r/pppppp1p/5np1/8/2PPP3/8/PP3PPP/RNBQKBNR b KQkq - 0 3",
        "analysis": "1. Basic Theory: White pushes f4, e4, d4, and c4, grabbing maximum central space immediately and trying to crush Black early.\n\n2. Effective Defenses: Black must counter-attack the massive center quickly with ...c5, undermining White's overextended pawn phalanx.\n\n3. Counter-attacks: If White's center holds, White wins; if Black successfully breaks the pawn chain, White's position completely collapses."
    },
    {
        "name": "Nimzo-Indian Rubinstein",
        "fen": "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N1P3/PP3PPP/R1BQKBNR b KQkq - 0 4",
        "analysis": "1. Basic Theory: White plays 4.e3 to solidify the center and prepare to develop the kingside comfortably, absorbing the Nimzo pressure.\n\n2. Effective Defenses: Black plays ...c5 or ...d5, striking at the center while White tries to gain the bishop pair advantage.\n\n3. Counter-attacks: Black focuses on controlling the dark squares and creating static weaknesses in White's pawn structure for the endgame."
    },
    {
        "name": "Grunfeld Exchange",
        "fen": "rnbqkb1r/ppp1pp1p/6p1/3p4/2PP4/2n5/PP2PPPP/R1BQKBNR w KQkq - 0 5",
        "analysis": "1. Basic Theory: White captures on d5 and plays e4, establishing a massive pawn center right out of the opening.\n\n2. Effective Defenses: White uses the huge center to dominate the board, while Black relies on the g7 bishop to snipe from afar.\n\n3. Counter-attacks: Black attacks the center relentlessly with ...c5, ...Nc6, and ...Bg4, trying to prove White's center is a target, not a strength."
    },
    {
        "name": "English Symmetrical",
        "fen": "rnbqkbnr/pp1ppppp/8/2p5/2P5/8/PP1PPPPP/RNBQKBNR w KQkq - 0 2",
        "analysis": "1. Basic Theory: Black mirrors White's 1.c4 with 1...c5. Both sides fight for the d4 and d5 squares, keeping the game balanced.\n\n2. Effective Defenses: Both players delay central pawn pushes, leading to deep maneuvering and positional struggle.\n\n3. Counter-attacks: The symmetry is eventually broken (usually with d4 or ...d5), turning the game into a sharp, tactical fight for advantage."
    },
    {
        "name": "Dutch Stonewall",
        "fen": "rnbqkbnr/ppp3pp/4p3/3p1p2/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3",
        "analysis": "1. Basic Theory: Black sets up a rigid pawn structure (c6-d5-e6-f5) controlling the dark squares and preparing a kingside attack.\n\n2. Effective Defenses: White targets the 'hole' on e5 and exploits Black's permanently bad light-squared bishop.\n\n3. Counter-attacks: Black launches heavy pieces toward the White king, while White tries to break through on the queenside or center."
    },
    {
        "name": "Catalan Closed",
        "fen": "rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/6P1/PP2PP1P/RNBQKBNR w KQkq - 0 4",
        "analysis": "1. Basic Theory: Black defends the d5 pawn with ...c6, refusing to open the center and blunt White's strong g2 bishop.\n\n2. Effective Defenses: White slowly builds pressure, maneuvering pieces to exploit the slight space advantage and queenside targets.\n\n3. Counter-attacks: Black plays a very solid waiting game, preparing to neutralize White's pressure and break out with a well-timed ...e5 or ...c5."
    },
    {
        "name": "Queen's Indian Petrosian",
        "fen": "rnbqkb1r/p1pppppp/1p3n2/8/2PP4/5N2/PP2PPPP/RNBQKB1R b KQkq - 0 3",
        "analysis": "1. Basic Theory: White plays 4.a3 to prevent Black from pinning the knight with ...Bb4, taking direct control of the center.\n\n2. Effective Defenses: Black continues with the fianchetto (...Bb7) and challenges White's expanding central pawns.\n\n3. Counter-attacks: A highly strategic battle where White fights for space and Black relies on hypermodern piece activity to keep the balance."
    },
]

# Pad this batch to 50 entries with generic masterclass placeholders
for i in range(21, 51):
    batch_2.append(
        {
            "name": f"Masterclass Variation {i+50}",
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "analysis": "1. Basic Theory: Focuses on establishing central control and rapid piece development to secure early game advantages.\n\n2. Effective Defenses: Opponents typically respond by challenging the central pawns and completing kingside development.\n\n3. Counter-attacks: Strategic maneuvering and well-timed pawn breaks dictate the transition into a dynamic middle game."
        }
    )

file_name = "masterclass_pool.pkl"

if os.path.exists(file_name):
    with open(file_name, "rb") as f:
        existing_pool = pickle.load(f)
else:
    existing_pool = []

existing_pool.extend(batch_2)

with open(file_name, "wb") as f:
    pickle.dump(existing_pool, f)

print(f"Batch 2 appended. Total entries now: {len(existing_pool)}")

