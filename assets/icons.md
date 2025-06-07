converting svg to png:


cd "/Users/claytongoddard/Library/Application Support/Anki2/addons21/Main_Toolbar/icons" && for svg in angle-double-right.svg bent_menu-burger.svg gallery.svg graphic-style.svg image.svg picture.svg sparkles_dark.svg sparkles_light.svg; do rsvg-convert "$svg" -w 64 -h 64 -o "${svg%.svg}.png"; done