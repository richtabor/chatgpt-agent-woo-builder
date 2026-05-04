# Interval

```yaml
name: Interval
description: A bold WooCommerce store for urban runners buying weather-aware training gear, recovery tools, and race-day kits.
collection: bold
colors:
  default:
    background: "#F2EEE6"
    foreground: "#101214"
  surfaces:
    asphalt:
      background: "#101214"
      foreground: "#F2EEE6"
      border: "#2A2E32"
    signal:
      background: "#E85B2B"
      foreground: "#101214"
      button:
        background: "#E85B2B"
        foreground: "#101214"
      link: "#101214"
    mist:
      background: "#DDE6E8"
      foreground: "#101214"
      border: "#AAB6BA"
typography:
  heading:
    category: grotesque-sans
    fontFamily: "Archivo, Inter, sans-serif"
    weights: "600-800"
    source: "Google Fonts"
    variable: true
  body:
    category: geometric-sans
    fontFamily: "Inter, sans-serif"
    weights: "400-600"
    source: "Google Fonts"
    variable: true
rounded:
  buttons: pill
  cards: tight
  inputs: pill
spacing:
  density: compact
  rhythm: staggered
components:
  button:
    surface: "{colors.surfaces.signal.button.background}"
    text: "{colors.surfaces.signal.button.foreground}"
    radius: "{rounded.buttons}"
  navigation:
    surface: "{colors.default.background}"
    text: "{colors.default.foreground}"
  card:
    surface: "{colors.surfaces.asphalt.background}"
    text: "{colors.surfaces.asphalt.foreground}"
    radius: "{rounded.cards}"
  input:
    surface: "{colors.surfaces.mist.background}"
    text: "{colors.default.foreground}"
    radius: "{rounded.inputs}"
```

Interval is an urban running store organized around conditions, rituals, and race-week systems rather than a flat athletics catalog. The experience should feel fast, metropolitan, high-contrast, and practical.

Core homepage story:

1. Lead with city-run urgency and weather-aware outfitting.
2. Route shoppers into conditions first: humid dawn, cold rain, track night, and race week.
3. Back that up with modular systems: apparel, carry and hydration, recovery, and race-day prep.
4. Keep the layout compact, sharp, and useful on mobile.
