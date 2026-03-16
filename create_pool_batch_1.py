import pickle

batch_1 = [
    {
        "name": "Sicilian Defense", 
        "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2", 
        "analysis": "1. Basic Theory: The Sicilian (1...c5) immediately challenges White's central control, creating an asymmetrical and dynamic pawn structure.\n\n2. Effective Defenses: White often responds with the Open Sicilian (2.Nf3 and 3.d4), aiming for rapid piece development and sharp attacking chances.\n\n3. Counter-attacks: Black utilizes the semi-open c-file, targeting the queenside and preparing powerful pawn breaks like ...d5 or ...b5."
    },
    {
        "name": "Ruy Lopez (Spanish Opening)", 
        "fen": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 1 3", 
        "analysis": "1. Basic Theory: One of the oldest openings. White develops the bishop to b5, pressuring the knight that defends the e5 pawn.\n\n2. Effective Defenses: Black relies on the Berlin Defense for a solid endgame, or the Morphy Defense (3...a6) to challenge the bishop.\n\n3. Counter-attacks: Black aims for the Marshall Attack, sacrificing a pawn for a vicious kingside initiative."
    },
    {
        "name": "French Defense", 
        "fen": "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", 
        "analysis": "1. Basic Theory: A solid, counter-attacking opening where Black accepts a cramped position (1...e6) for long-term structural stability.\n\n2. Effective Defenses: White usually establishes a strong pawn center with d4 and e5, suffocating Black's light-squared bishop.\n\n3. Counter-attacks: Black relentlessly attacks White's pawn chain from the base using ...c5 and ...f6, aiming to collapse the center."
    },
    {
        "name": "Caro-Kann Defense", 
        "fen": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", 
        "analysis": "1. Basic Theory: An extremely solid response to e4 (1...c6). It prioritizes pawn structure and king safety over rapid development.\n\n2. Effective Defenses: White can choose the Advance Variation (3.e5) to gain space, or the Exchange Variation for a quieter, positional game.\n\n3. Counter-attacks: Black seeks a favorable endgame, holding key squares like d5 and punishing overextended white pawns."
    },
    {
        "name": "Queens Gambit", 
        "fen": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2", 
        "analysis": "1. Basic Theory: White offers the c4 pawn to deflect Black's d5 pawn, aiming for central domination and rapid piece activity.\n\n2. Effective Defenses: Black can decline (QGD) to maintain a solid pawn structure, or accept (QGA) and focus on rapid development.\n\n3. Counter-attacks: Black relies on the ...c5 pawn break to challenge the center and free the queenside pieces."
    },
    {
        "name": "Kings Indian Defense", 
        "fen": "rnbqkb1r/pppppp1p/5np1/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3", 
        "analysis": "1. Basic Theory: A hypermodern, aggressive setup. Black allows White a massive pawn center, intending to dismantle it later.\n\n2. Effective Defenses: White builds a broad center (c4, d4, e4) and tries to suffocate Black positionally on the queenside.\n\n3. Counter-attacks: Black launches chaotic, pawn-storm attacks on the kingside, heavily relying on the fianchettoed dark-squared bishop."
    },
    {
        "name": "Italian Game", 
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3", 
        "analysis": "1. Basic Theory: Focuses on rapid development. The bishop moves to c4, immediately eyeing Black's weakest point, the f7 pawn.\n\n2. Effective Defenses: Black plays solidly with the Giuoco Piano, aiming for central symmetry, or the Two Knights Defense to force complications.\n\n3. Counter-attacks: Black frequently strikes back in the center with ...d5, or launches the aggressive Traxler Counterattack."
    },
    {
        "name": "Nimzo-Indian Defense", 
        "fen": "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/2N5/PP2PPPP/R1BQKBNR w KQkq - 2 4", 
        "analysis": "1. Basic Theory: Highly strategic. Black pins the c3 knight, preventing White from playing e4 and controlling the center remotely.\n\n2. Effective Defenses: White plays the Rubinstein (4.e3) or Classical system, aiming to gain the bishop pair and a strong center.\n\n3. Counter-attacks: Black inflicts doubled pawns on White's c-file and targets them, creating long-term structural weaknesses."
    },
    {
        "name": "Slav Defense", 
        "fen": "rnbqkbnr/pp2pppp/2p5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3", 
        "analysis": "1. Basic Theory: A rock-solid defense against the Queen's Gambit. Black supports the d5 pawn with ...c6, keeping the light-squared bishop free.\n\n2. Effective Defenses: White often plays the Exchange Variation to simplify the position, or the critical Main Line aiming for space.\n\n3. Counter-attacks: Black uses the active bishop and plans a well-timed ...e5 or ...c5 break to liberate the position."
    },
    {
        "name": "English Opening", 
        "fen": "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq - 0 1", 
        "analysis": "1. Basic Theory: A flank opening (1.c4). White controls the center indirectly, delaying pawn commitments to remain highly flexible.\n\n2. Effective Defenses: Black can respond symmetrically (1...c5) or aim for an Indian setup, preparing for a slow, strategic battle.\n\n3. Counter-attacks: Black often aims for a rapid ...d5 or ...e5 break, trying to seize the center while White plays on the flanks."
    },
    {
        "name": "Dutch Defense", 
        "fen": "rnbqkbnr/ppppp1pp/8/5p2/3P4/8/PPP1PPPP/RNBQKBNR w KQkq f6 0 2", 
        "analysis": "1. Basic Theory: An immediate, unbalanced challenge to White's center (1...f5). It is aggressive and carries significant positional risk.\n\n2. Effective Defenses: White frequently fianchettos the kingside bishop to control the central light squares and nullify Black's attack.\n\n3. Counter-attacks: Black aims for a direct, piece-heavy assault on the White king, often utilizing the Stonewall structure."
    },
    {
        "name": "Grunfeld Defense", 
        "fen": "rnbqkb1r/pppppp1p/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq - 2 3", 
        "analysis": "1. Basic Theory: A hypermodern masterpiece. Black deliberately allows White to build a massive pawn center to create a target.\n\n2. Effective Defenses: White solidifies the center and tries to use the space advantage to squeeze Black positionally.\n\n3. Counter-attacks: Black relentlessly attacks the central pawn mass with pieces and the ...c5 break, threatening to collapse White's position."
    },
    {
        "name": "Reti Opening", 
        "fen": "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1", 
        "analysis": "1. Basic Theory: Starts with 1.Nf3. White delays central pawns, preferring to control squares with pieces and fianchettoed bishops.\n\n2. Effective Defenses: Black often builds a strong center with ...d5 and ...c6, daring White to find a way to break it down.\n\n3. Counter-attacks: Black uses the central space to restrict White's pieces, eventually launching an attack if White plays too passively."
    },
    {
        "name": "Scandinavian Defense", 
        "fen": "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", 
        "analysis": "1. Basic Theory: An immediate challenge (1...d5). It eliminates White's e4 pawn early and forces the game into open territory.\n\n2. Effective Defenses: White gains time by attacking Black's early-developed Queen, aiming for a rapid lead in development.\n\n3. Counter-attacks: Black relies on a solid pawn structure and active piece play, often castling queenside to launch a pawn storm."
    },
    {
        "name": "Vienna Game", 
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 2", 
        "analysis": "1. Basic Theory: White develops the knight to c3 to protect e4 and prepare an aggressive f4 push. It avoids standard Spanish lines.\n\n2. Effective Defenses: Black plays ...Nf6 and ...Nc6, maintaining central tension and preventing White from gaining an easy advantage.\n\n3. Counter-attacks: Black often strikes with a central ...d5 break, aiming to exploit the weaknesses created by White's f4 advance."
    },
    {
        "name": "Alekhine Defense", 
        "fen": "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2", 
        "analysis": "1. Basic Theory: Highly provocative. Black plays 1...Nf6 immediately, luring White's central pawns forward to overextend them.\n\n2. Effective Defenses: White accepts the challenge, building a large pawn center but must play carefully to avoid overstretching.\n\n3. Counter-attacks: Black chips away at the overextended pawn center using moves like ...d6 and ...c5, aiming to destroy it completely."
    },
    {
        "name": "Kings Gambit", 
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/4PP2/8/PPPP2PP/RNBQKBNR b KQkq f3 0 2", 
        "analysis": "1. Basic Theory: A romantic, chaotic opening. White sacrifices the f-pawn to secure central dominance and open the f-file for attack.\n\n2. Effective Defenses: Black can accept the gambit and hold the pawn, or decline it to maintain a stable, solid position.\n\n3. Counter-attacks: Black frequently sacrifices material back (like ...d5) to disrupt White's coordination and seize the initiative."
    },
    {
        "name": "Scotch Game", 
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/3PP3/5N2/PPP2PPP/RNBQKB1R b KQkq d3 0 3", 
        "analysis": "1. Basic Theory: White forces the center open immediately with 3.d4. It clears lines rapidly and leads to sharp tactical skirmishes.\n\n2. Effective Defenses: Black responds actively with ...exd4, focusing on quick development and avoiding passive, cramped positions.\n\n3. Counter-attacks: Black often targets the centralized White pieces, preparing strong counter-punches with ...d5 or placing the bishop on c5."
    },
    {
        "name": "Catalan Opening", 
        "fen": "rnbqkb1r/pppp1ppp/4pn2/8/2PP4/6P1/PP2PP1P/RNBQKBNR b KQkq - 0 3", 
        "analysis": "1. Basic Theory: Combines d4 principles with a kingside fianchetto. White seeks long-term positional pressure using the g2 bishop.\n\n2. Effective Defenses: Black plays the Open Catalan (capturing on c4) or the Closed Catalan, fighting for space on the queenside.\n\n3. Counter-attacks: Black neutralizes the long diagonal and uses the c-file to create counterplay against White's queenside structure."
    },
    {
        "name": "London System", 
        "fen": "rnbqkbnr/pppp1ppp/4p3/8/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 1 3", 
        "analysis": "1. Basic Theory: A highly systematic, solid setup. White builds a strong 'pyramid' pawn structure (d4, e3, c3) and develops the bishop to f4.\n\n2. Effective Defenses: Black aims to disrupt the structure early with ...c5, or prepares a central ...e5 break to challenge White's setup.\n\n3. Counter-attacks: Black often targets the b2 pawn or launches a queenside minority attack to crack White's solid formation."
    },
    {
        "name": "Modern Defense (Pirc)", 
        "fen": "rnbqkbnr/pppppp1p/6p1/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", 
        "analysis": "1. Basic Theory: Black delays central pawn moves and fianchettos the bishop on g7, allowing White to build a large center.\n\n2. Effective Defenses: White creates a broad pawn center (d4, e4) and prepares to attack Black's kingside directly.\n\n3. Counter-attacks: Black strikes back at the center with ...c5 or ...e5, acting as a coiled spring ready to release energy."
    },
    {
        "name": "Bishops Opening", 
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2", 
        "analysis": "1. Basic Theory: White immediately develops the bishop to c4, eyeing the f7 pawn and delaying the knight development.\n\n2. Effective Defenses: Black counters securely with ...Nf6, preparing to meet White's setup with solid central control.\n\n3. Counter-attacks: Black often plays for a quick ...d5 break or forces transitions into favorable Italian Game lines."
    },
    {
        "name": "Evans Gambit", 
        "fen": "r1bqk1nr/pppp1ppp/2n5/2b1p3/1PB1P3/5N2/P1PP1PPP/RNBQK2R b KQkq b3 0 4", 
        "analysis": "1. Basic Theory: An aggressive pawn sacrifice in the Italian Game. White gives up the b-pawn for rapid development and a dominant center.\n\n2. Effective Defenses: Black can accept the pawn and try to weather the storm, or decline it to keep the position closed.\n\n3. Counter-attacks: Black must return the material at the right time to catch up in development and launch a counter-offensive."
    },
    {
        "name": "Danish Gambit", 
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq d3 0 2", 
        "analysis": "1. Basic Theory: White sacrifices one or two pawns in the opening for insanely fast development and two raking bishops.\n\n2. Effective Defenses: Black must not get greedy; accepting both pawns requires extreme precision to survive the early onslaught.\n\n3. Counter-attacks: Black defends accurately and pushes ...d5 to break White's coordination and equalize into a superior endgame."
    },
    {
        "name": "Petrov Defense", 
        "fen": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", 
        "analysis": "1. Basic Theory: A symmetrical and rock-solid defense. Black ignores White's threat on e5 and counter-attacks White's e4 pawn immediately.\n\n2. Effective Defenses: White plays d3 or Nxe5 to force an early structural decision, keeping the game fundamentally balanced.\n\n3. Counter-attacks: Often leads to drawish, symmetrical structures, but Black can create imbalances if White over-pushes."
    },
    {
        "name": "Philidor Defense", 
        "fen": "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3", 
        "analysis": "1. Basic Theory: Black defends the e5 pawn with ...d6. It is a very solid but somewhat passive opening choice.\n\n2. Effective Defenses: White develops naturally and tries to exploit Black's cramped position by maintaining central tension.\n\n3. Counter-attacks: Black accepts a cramped setup, aiming for a slow, strategic buildup and avoiding sharp early tactical traps."
    },
    {
        "name": "Chigorin Defense", 
        "fen": "r1bqkbnr/ppp1pppp/2n5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 1 3", 
        "analysis": "1. Basic Theory: An aggressive response to the Queen's Gambit. Black develops the knight to c6, blocking the c-pawn but fighting for the center.\n\n2. Effective Defenses: White plays Nc3 or cxd5, challenging Black's unusual setup and trying to secure a classic central advantage.\n\n3. Counter-attacks: Black aims for rapid piece activity and often sacrifices the bishop pair to ruin White's pawn structure."
    },
    {
        "name": "Colle System", 
        "fen": "rnbqkbnr/ppp1pppp/8/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R b KQkq - 1 2", 
        "analysis": "1. Basic Theory: A universal opening setup for White. It focuses on a solid d4-e3-c3 pawn structure, keeping things closed initially.\n\n2. Effective Defenses: Black develops actively, often playing ...c5 to challenge the center and prevent White's ideal setup.\n\n3. Counter-attacks: White aims for a strong e4 pawn break to launch a kingside attack, while Black counters on the queenside."
    },
    {
        "name": "Trompowsky Attack", 
        "fen": "rnbqkb1r/pppppppp/5n2/8/3P4/5B2/PPP1PPPP/RN1QK1NR b KQkq - 2 2", 
        "analysis": "1. Basic Theory: White immediately plays Bg5 against 1...Nf6. It aims to double Black's pawns and bypass deep main-line Indian defenses.\n\n2. Effective Defenses: Black can play ...Ne4 to challenge the bishop or accept the doubled pawns for the bishop pair advantage.\n\n3. Counter-attacks: Leads to original, unbalanced positional struggles where Black relies on dynamic piece play."
    },
    {
        "name": "Benoni Defense", 
        "fen": "rnbqkbnr/pp1ppppp/8/2p5/3P4/8/PPP1PPPP/RNBQKBNR w KQkq c6 0 2", 
        "analysis": "1. Basic Theory: An aggressive, asymmetrical response to 1.d4. Black sacrifices central space for active piece play and pressure on the dark squares.\n\n2. Effective Defenses: White establishes a strong d5 pawn wedge, restricting Black and preparing a central or kingside push.\n\n3. Counter-attacks: Black relies on a queenside pawn majority and the fianchettoed bishop on g7 to create relentless dynamic counterplay."
    },
    {
        "name": "Benko Gambit", 
        "fen": "rnbqkb1r/p2ppppp/5n2/1ppP4/2P5/8/PP2PPPP/RNBQKBNR w KQkq b6 0 4", 
        "analysis": "1. Basic Theory: Black sacrifices a queenside pawn early to open the a and b files for massive, long-term positional pressure.\n\n2. Effective Defenses: White can accept the gambit and endure the pressure, or decline it to keep the queenside closed.\n\n3. Counter-attacks: Unlike tactical gambits, the Benko provides Black with enduring positional compensation that lasts deep into the endgame."
    },
    {
        "name": "Birds Opening", 
        "fen": "rnbqkbnr/pppppppp/8/8/5P2/8/PPPPP1PP/RNBQKBNR b KQkq f3 0 1", 
        "analysis": "1. Basic Theory: White begins with 1.f4, immediately fighting for the e5 square from the flank, similar to a reversed Dutch Defense.\n\n2. Effective Defenses: Black often plays 1...d5 to secure the center or From's Gambit (1...e5) to create immediate tactical chaos.\n\n3. Counter-attacks: Black focuses on exploiting the weakened e1-h4 diagonal around White's king, aiming for rapid central counterplay."
    },
    {
        "name": "Larsens Opening", 
        "fen": "rnbqkbnr/pppppppp/8/8/8/1P6/P1PPPPPP/RNBQKBNR b KQkq - 0 1", 
        "analysis": "1. Basic Theory: White plays 1.b3, preparing to fianchetto the bishop to b2 to control the long diagonal and the center remotely.\n\n2. Effective Defenses: Black traditionally occupies the center with ...e5 and ...d5, establishing a classical strong setup.\n\n3. Counter-attacks: Black uses the strong center to restrict White's bishop, preparing direct attacks if White plays too passively."
    },
    {
        "name": "Kings Indian Attack", 
        "fen": "rnbqkbnr/pppppppp/8/8/8/5NP1/PPPPPP1P/RNBQKB1R b KQkq - 0 1", 
        "analysis": "1. Basic Theory: A versatile setup for White (Nf3, g3, Bg2, d3), essentially playing the King's Indian Defense with colors reversed.\n\n2. Effective Defenses: Black builds a strong pawn center and develops naturally, treating the game as a flexible strategic battle.\n\n3. Counter-attacks: White often launches a potent kingside pawn storm (e4-e5), while Black responds with aggressive queenside expansion."
    },
    {
        "name": "Grob Opening", 
        "fen": "rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3 0 1", 
        "analysis": "1. Basic Theory: A highly unorthodox and dubious opening (1.g4). White claims space on the kingside but severely weakens the king's safety.\n\n2. Effective Defenses: Black easily occupies the center with ...d5 or ...e5, ignoring White's flank attack.\n\n3. Counter-attacks: Black targets the exposed g4 pawn and exploits White's lack of central control to dominate the board rapidly."
    },
    {
        "name": "Englund Gambit", 
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2", 
        "analysis": "1. Basic Theory: Black responds to 1.d4 with 1...e5, offering a pawn immediately to open lines and drag White out of their comfort zone.\n\n2. Effective Defenses: White accepts the pawn and focuses on solid development, avoiding the numerous early tactical traps.\n\n3. Counter-attacks: Black relies on tricky, fast-paced piece play to punish an unprepared White player, though objectively it is dubious."
    },
    {
        "name": "Albin Countergambit", 
        "fen": "rnbqkbnr/ppp2ppp/8/3pp3/2PP4/8/PP2PPPP/RNBQKBNR w KQkq d6 0 3", 
        "analysis": "1. Basic Theory: Black strikes back against the Queen's Gambit with 2...e5, sacrificing a pawn to plant a disruptive wedge on d4.\n\n2. Effective Defenses: White develops the kingside (Nf3, g3) to contain the d4 pawn and prepare to win it or play around it.\n\n3. Counter-attacks: Black uses the d4 pawn to cramp White's position, creating unique tactical opportunities like the famous Lasker Trap."
    },
    {
        "name": "Budapest Gambit", 
        "fen": "rnbqkb1r/pppp1ppp/8/4p3/2P1n3/5N2/PP1P1PPP/RNBQKB1R w KQkq - 1 4", 
        "analysis": "1. Basic Theory: Black sacrifices a pawn (1.d4 Nf6 2.c4 e5) to force White's pieces into awkward positions while trying to defend it.\n\n2. Effective Defenses: White can hold the pawn or return it cleanly for a solid developmental advantage and better structure.\n\n3. Counter-attacks: Black rapidly maneuvers pieces to target the e5 pawn, often regaining it and equalizing the game comfortably."
    },
    {
        "name": "Bogo-Indian Defense", 
        "fen": "rnbqk2r/pppp1ppp/4pn2/8/1bPP4/5N2/PP2PPPP/RNBQKB1R w KQkq - 2 4", 
        "analysis": "1. Basic Theory: A solid cousin of the Nimzo-Indian. Black plays ...Bb4+ to disrupt White's development and exchange pieces.\n\n2. Effective Defenses: White blocks with Bd2 or Nbd2, aiming to secure the bishop pair and maintain a space advantage.\n\n3. Counter-attacks: Black achieves a solid, flexible position, focusing on neutralizing White's center and preparing pawn breaks like ...c5 or ...e5."
    },
    {
        "name": "Queens Indian Defense", 
        "fen": "rnbqkb1r/p1pppppp/1p3n2/8/2PP4/5N2/PP2PPPP/RNBQKB1R b KQkq - 0 3", 
        "analysis": "1. Basic Theory: A highly respected hypermodern defense. Black fianchettos the queenside bishop to control the critical e4 and d5 squares.\n\n2. Effective Defenses: White usually counters with g3, setting up a rival fianchetto to contest the long light-squared diagonal.\n\n3. Counter-attacks: The game becomes a deep strategic battle for central squares, with Black maintaining extreme flexibility and solid defense."
    },
    {
        "name": "Torre Attack", 
        "fen": "rnbqkb1r/pppppppp/5n2/8/3P1B2/8/PPP1PPPP/RN1QKBNR b KQkq - 2 2", 
        "analysis": "1. Basic Theory: White plays Bg5 early against ...Nf6, avoiding complex main lines while building a solid, hard-to-crack position.\n\n2. Effective Defenses: Black challenges the center with ...c5 or prepares a solid setup with ...e6 and ...d5 to limit White's aggression.\n\n3. Counter-attacks: White aims for a kingside attack using the e4 break, while Black counters strongly on the queenside or center."
    },
    {
        "name": "Veresov Attack", 
        "fen": "rnbqkb1r/pppppppp/5n2/8/3P4/2N5/PPP1PPPP/R1BQKBNR b KQkq - 2 2", 
        "analysis": "1. Basic Theory: White plays Nc3 and Bg5, aiming for rapid, aggressive piece play and an early e4 pawn push to dominate the center.\n\n2. Effective Defenses: Black usually responds with ...d5 or ...c5, directly challenging White's central ambitions.\n\n3. Counter-attacks: Black often targets the somewhat misplaced Nc3 knight and takes advantage of White's slightly weakened queenside structure."
    },
    {
        "name": "Blackmar-Diemer Gambit", 
        "fen": "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2", 
        "analysis": "1. Basic Theory: A fierce, speculative gambit. White sacrifices the e-pawn and f-pawn to open lines and launch a terrifying early attack.\n\n2. Effective Defenses: Black accepts the pawn and focuses entirely on returning material to simplify into a winning endgame.\n\n3. Counter-attacks: White relies on piece activity and open files. If Black survives the initial onslaught, White's position collapses."
    },
    {
        "name": "Sicilian Najdorf", 
        "fen": "rnbqkb1r/1p2pppp/p2p1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6", 
        "analysis": "1. Basic Theory: The Cadillac of chess openings. Black plays ...a6 to control b5 and keep the options open for a central or queenside strike.\n\n2. Effective Defenses: White employs sharp attacks like the English Attack (Be3, f3, g4) or positional lines (Be2) to squeeze Black.\n\n3. Counter-attacks: Black uses the legendary flexibility of the Najdorf to generate lethal counterplay on the c-file and the center."
    },
    {
        "name": "Sicilian Dragon", 
        "fen": "rnbqkb1r/pp2pp1p/3p1np1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 0 6", 
        "analysis": "1. Basic Theory: Black fianchettos the bishop on g7, aiming it like a sniper down the long diagonal toward White's queenside.\n\n2. Effective Defenses: White's most dangerous response is the Yugoslav Attack (Be3, f3, Qd2), preparing to castle long and storm the kingside.\n\n3. Counter-attacks: Black sacrifices exchanges (like ...Rxc3) to destroy White's king cover, leading to extremely sharp, double-edged races."
    },
    {
        "name": "French Advance", 
        "fen": "rnbqkbnr/ppp2ppp/4p3/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3", 
        "analysis": "1. Basic Theory: White pushes e5 immediately, gaining a significant space advantage and locking the center early in the game.\n\n2. Effective Defenses: Black immediately undermines White's pawn chain with the classic ...c5 and ...f6 breaks.\n\n3. Counter-attacks: The battle revolves entirely around the d4 and e5 pawns. If White holds the center, they win; if Black breaks it, Black wins."
    },
    {
        "name": "Caro-Kann Advance", 
        "fen": "rnbqkbnr/pp2pppp/2p5/3pP3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3", 
        "analysis": "1. Basic Theory: White plays e5, taking space and making it harder for Black to develop the kingside pieces smoothly.\n\n2. Effective Defenses: Black plays ...Bf5 or ...c5, ensuring the light-squared bishop is active before closing the pawn structure.\n\n3. Counter-attacks: Black aims for a very solid position, slowly preparing to undermine White's extended pawns with well-timed breaks."
    },
    {
        "name": "Ruy Lopez Berlin", 
        "fen": "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", 
        "analysis": "1. Basic Theory: The 'Berlin Wall'. Black avoids sharp middlegame theory, forcing an early queen exchange into a notorious endgame.\n\n2. Effective Defenses: White tries to exploit Black's doubled pawns and lack of castling rights in the endgame structure.\n\n3. Counter-attacks: Black relies on the incredibly resilient bishop pair and solid pawn structure, making it extremely difficult for White to break through."
    },
    {
        "name": "Queens Gambit Accepted", 
        "fen": "rnbqkbnr/ppp1pppp/8/8/2pP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3", 
        "analysis": "1. Basic Theory: Black temporarily wins a pawn by capturing on c4, choosing rapid development over defending a central pawn chain.\n\n2. Effective Defenses: White plays e3 or e4 to regain the pawn immediately while building a strong, commanding center.\n\n3. Counter-attacks: Black strikes back at White's center with ...c5 or ...e5, aiming for an open, active game rather than holding the gambit pawn."
    },
    {
        "name": "Queens Gambit Declined", 
        "fen": "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq - 0 3", 
        "analysis": "1. Basic Theory: Black defends the d5 pawn with ...e6, maintaining a rock-solid central presence but burying the light-squared bishop.\n\n2. Effective Defenses: White plays Nc3 and Bg5, creating pressure on d5 and preparing the standard minority attack on the queenside.\n\n3. Counter-attacks: Black plays patiently, aiming to free the problem bishop and using the central stability to prepare safe counterplay."
    }
]

with open('masterclass_pool.pkl', 'wb') as f:
    pickle.dump(batch_1, f)
    
print('Batch 1 (50 Openings) successfully created and saved to masterclass_pool.pkl')

