# Installer branding assets

[English](README.md) | [简体中文](README.zh-CN.md)

`ios.png` is the branding image provided by the project, used as the desktop
entry icon. `banner.json` is an ASCII sampling of that image's blue outline
(`#`) and golden starlight (`*`), generated at roughly a 1:2 terminal character
ratio in 20-, 32-, and 48-column variants, requiring no Pillow, external fonts,
or image libraries at runtime. This ASCII asset is kept for historical
reference; since .10, the current terminal welcome page shows text only and no
longer draws graphics. The desktop shortcut still uses the original PNG.
Colors are only enabled on interactive terminals that support them;
`NO_COLOR` disables colors.
