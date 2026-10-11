# Headless test bench (Azahar with an extended RPC)

Lets you test the game **without human intervention**: press buttons, touch the screen, advance frames
deterministically and at maximum speed, capture both screens, save/load states, read/write RAM and use the
**developer's own debug menu** as a "cheat" (instant battles, map viewer, value and flag editors).

## Pieces
| File | What it is |
|---|---|
| `azahar-harness.patch` | Patch on Azahar `2126.1.2` (`src/` branch): extended RPC + harness mode |
| `azahar_rpc.py` | Python RPC client (`launch()`, `press()`, `run()`, `screenshot()`, `save_state()`...) |
| `h.py` | CLI of chainable commands (see below) |
| `testmods/debug_menu/` | Test-ONLY overlay: boot opens the debug menu `test_menu_a2` |
| `testmods/debug_boot/` | Test-ONLY overlay: the developer's chapter selector (`dbg_st`) |
| `bisect_boot.py` | Bisection of the mod files that cause a PANIC at boot |
| `test_tutorial_battle.py` | Automatic tutorial robattle (detects PANIC / unmapped memory / hang) |
| `sweep_maps.py` | Loads the ~167 maps with the map viewer and detects failures; captures every map |
| `test_codebin_variant.py` | Tests code.bin variants in the tutorial robattle (`--mode raw` reproduces crash #2) |
| `smoke.py` | Final smoke suite: normal boot + Continue with the save + menu, tutorial and 20 maps |
| `compare_newgame.py` | New game with the JAPANESE game (mods set aside) and with the patch, same button presses: compares e.g. the Medabots of the first robattle |
| `test_scene.py` | Jumps to a story event (developer's chapter selector with its chapter 2 branch rewritten for the run: the player's Medal name, story step, warp to the event's map, the map's event script) and plays it pressing A: the patch, the Japanese game (`--jp`) or another patch (`--mod-romfs/--mod-exefs`, `--no-update`), Kuwagata or `--kabuto` |

## Building the bench Azahar
```bash
mkdir -p experiments/harness && cd experiments/harness
git clone --depth 1 --branch 2126.1.2 --recurse-submodules --shallow-submodules \
    https://github.com/azahar-emu/azahar.git azahar-src
cd azahar-src && git apply ../../../tools/harness/azahar-harness.patch
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DUSE_SYSTEM_QT=ON \
  -DCMAKE_PREFIX_PATH=/opt/homebrew/opt/qt -DENABLE_QT_TRANSLATION=OFF -DENABLE_WEB_SERVICE=OFF \
  -DCITRA_WARNINGS_AS_ERRORS=OFF -DENABLE_LTO=OFF -DENABLE_QT_UPDATE_CHECKER=OFF \
  -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
cmake --build build --target citra_meta -j 9          # ~20 min the first time, ~2 min incremental
```
- `externals/teakra` uses git-lfs: if the checkout fails, `git -c filter.lfs.smudge= -c filter.lfs.process=
  -c filter.lfs.required=false reset --hard <commit>` inside the submodule.
- Portable mode: on macOS Azahar does a `chdir` to the folder containing the `.app`, so the isolated user
  folder is a link `build/bin/Release/user -> experiments/harness/run/user`.

## Isolated environment (`experiments/harness/run/user`)
Its own config (RPC enabled, no confirmations), a copy of `nand`/`sysdata` and of the user's save, the
1.3.0 update installed and its own mods. **It never touches the user's Azahar.**
Install a CIA on the bench: `azahar -i <cia>` with the bench binary (thanks to the `user` link).
The game file it boots is `roms/Medarot 9 - Kuwagata Ver. (Japan).3ds`; set `M9_BENCH_ROM=<path>` to boot another
copy (a `.3ds` or the program `.cxi` extracted from a `.cia`), e.g. when the card that holds the dump is not mounted.
Deploy the patch to the bench: `python python/deploy-es.py --fps60 --mods-dir experiments/harness/run/user/load/mods`.

## Harness mode (`AZAHAR_HARNESS=1`, set by `launch()`)
- Invisible window (opacity 0), unfocused, click-through and no Dock icon (`LSUIElement`).
- Any modal dialog is **logged** to `user/log/harness_dialogs.txt` and closed automatically.
- `launch()` first kills any other bench instance (never the user's).

## RPC (UDP 45987)
Already present: `ReadMemory`(1), `WriteMemory`(2), `ProcessList`(3), `SetGetProcess`(4). Added:
`SetInput`(100) buttons/Circle Pad/touch · `Screenshot`(101) PNG · `RunFrames`(102) deterministic advance with no
limiter · `Pause`(103)/`Resume`(104) · `SaveState`(105)/`LoadState`(106) · `SetSpeed`(107) · `Status`(108).
Implementation notes:
- `RunFrames` waits for the frame counter to **change** (it can go backwards when a state is loaded).
- Saving/loading a state releases step-by-step mode while the emulation loop handles the signal.
- The RPC server survives the deserialization of a state (otherwise the load deadlocks).

## `h.py` CLI
```bash
python tools/harness/h.py launch run 400 shot title         # start (paused) and capture at 400 frames
python tools/harness/h.py press START wait 150 shot menu    # press and capture (experiments/harness/shots/)
python tools/harness/h.py hold A 30 | mash A 10 40 | stick 0 1 20 | tap 160 120
python tools/harness/h.py save 1 | load 1 | status | dialogs | quit
python tools/harness/h.py testmod debug_menu on              # developer debug menu (tests only)
```

> **`testmod <name> off`** restores the `.testmod_bak` copy or, if there is none, removes the file ONLY if it is the
> overlay's. Until 8-Oct-2026 it always deleted it: `smoke.py`/`menu_tour.py` (which start with `off`) removed the
> DEPLOYED `spt/bootKWG.spt` and tested with the original boot script. After deploying to the bench, check that
> `load/mods/.../romfs/spt/bootKWG.spt` exists.

## Developer debug menu (`test/spt/test_menu_a2.spt`)
Opened with the `debug_menu` overlay (it only changes arguments/command names of `spt/bootKWG.spt`: same
number of instructions, so no relative jump shifts).
- Menu 1: start on a map (1VS1, 2VS2, 3VS3...), **Robattle** (test, normal, elimination, teams,
  **tutorial**, auto, aerial, diving...), **map viewer** (map number: UP/DOWN changes the digit,
  RIGHT/LEFT selects it; A shows it), model and character viewers, Medawatch, title, status.
- Menu 2 (`>NEXT`): network/effects/sound tests, **value editor** and **flag editor**.

## Test recipes
- **Before delivering a build**: `python tools/harness/smoke.py` (review `experiments/harness/shots/smoke_*.png` by eye).
- Tutorial robattle: `python tools/harness/test_tutorial_battle.py --steps 400`.
- code.bin: `python tools/harness/test_codebin_variant.py --mode all [--text-clean]` (restores the deployed one at the end).
- Fidelity to the Japanese: `python tools/harness/compare_newgame.py` (screenshots in `shots/cmp_jp` and `shots/cmp_es`; the JP
  pass sets the bench mod aside and always restores it). While the JP pass runs, do not deploy to the bench: Azahar reads
  the mod files on demand.
- All maps: `python tools/harness/sweep_maps.py` (results in `experiments/harness/sweep_maps.json`).
- PANIC at boot: `tools/harness/bisect_boot.py` (bisection by mod files).
- A story event (cutscene) on its own: `python tools/harness/test_scene.py tracks|interview [--jp]` (presets = story step,
  warp and event script; a cutscene script cannot be started alone: without its map it crashes even in the Japanese game).
  The developer's selector always makes 3 harmless unmapped accesses when an option is chosen (filtered).
  "Without problems" only means no PANIC/unmapped/hang: check the screenshots to see that the event really played
  (a code.bin of the other edition loads the other boot script; both are overlaid).
