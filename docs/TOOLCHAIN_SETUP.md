# Campus Shield Toolchain Setup

This file records the external tools selected for the next major rebuild. These tools are not bundled with the game repository.

## Selected Tools

- Godot 4.6.2, macOS universal: https://github.com/godotengine/godot/releases/download/4.6.2-stable/Godot_v4.6.2-stable_macos.universal.zip
- Godot 4.6.2 export templates: https://github.com/godotengine/godot/releases/download/4.6.2-stable/Godot_v4.6.2-stable_export_templates.tpz
- Tiled 1.12.1, macOS 13+: https://github.com/mapeditor/tiled/releases/download/v1.12.1/Tiled-1.12.1_macOS-13%2B.zip
- LDtk 1.5.3, macOS: https://github.com/deepnight/ldtk/releases/download/v1.5.3/mac-distribution.zip
- Pixelorama 1.1.9, macOS: https://github.com/Orama-Interactive/Pixelorama/releases/download/v1.1.9/Pixelorama-Mac.dmg
- Audacity 3.7.7, macOS arm64: https://github.com/audacity/audacity/releases/download/Audacity-3.7.7/audacity-macOS-3.7.7-arm64.dmg
- Figma Desktop 126.2.10, macOS arm64: https://desktop.figma.com/mac-arm/Figma-126.2.10.zip
- Blender 5.1.1, macOS arm64: https://download.blender.org/release/Blender5.1/blender-5.1.1-macos-arm64.dmg

## Installation Notes

- Godot, Tiled, LDtk, Pixelorama, Figma, and Blender should be installed into `/Applications`.
- Godot export templates are imported from inside Godot after the editor opens.
- Audacity is used only for editing sound cues and does not need to be part of the game runtime.
- Aseprite is intentionally not listed because it is paid software; Pixelorama is the free replacement for this project.

## Intended Use

- Godot: next-generation game client, scene graph, UI, animation, input, export.
- Tiled / LDtk: room, floor, collision, patrol path, and trigger layout.
- Pixelorama: pixel sprites, icons, simple tile edits.
- Audacity: alert sounds, ambient audio, radio/announcement processing.
- Figma: UI concept boards and layout mockups.
- Blender: optional 2.5D reference renders or asset previsualization.
