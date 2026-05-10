# Digital Bonsai Tree

A procedurally generated interactive bonsai ecosystem built with Python and Arcade.

This project simulates the life of a digital bonsai tree with:

* recursive procedural growth
* dynamic weather
* day/night cycles
* wind animation
* resource management
* pruning mechanics
* environmental simulation
* animated leaves and rain particles

The tree evolves over time based on its environment and player interaction, creating a calm generative simulation inspired by nature.

---


## Features

### Procedural Tree Generation

* Recursive branch growth
* Randomized but controlled branch spreading
* Dynamic regrowth after pruning
* Terminal leaf cluster generation

### Environmental Simulation

* Sunny, cloudy, rainy, and stormy weather
* Smooth day/night cycle
* Dynamic sunlight calculation
* Wind simulation with branch sway
* Rain particle system

### Interactive Ecosystem

* Water and nutrient management
* Tree health simulation
* Growth affected by environmental conditions
* Storms can damage branches naturally

### Player Interaction

* Click to prune branches
* Water the tree
* Fertilize the soil
* Pause/unpause simulation

### Visual Effects

* Animated leaves
* Sky gradients
* Sun and moon movement
* Cloud rendering
* Pruning particle effects
* Dynamic ambient lighting

---

## Controls

| Key / Action | Function         |
| ------------ | ---------------- |
| Left Click   | Prune branch     |
| `W`          | Water tree       |
| `F`          | Fertilize tree   |
| `P`          | Pause simulation |
| `ESC`        | Quit             |

---

## Tech Stack

* Python
* Arcade
* Procedural Generation
* Recursive Data Structures
* Real-Time Simulation

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/prrabhagit/digital-bonsai-tree.git
cd digital-bonsai-tree
```

### 2. Install dependencies

```bash
pip install arcade
```

### 3. Run the project

```bash
python bonsai.py
```

---

## Project Structure

```bash
digital-bonsai-tree/
│
├── bonsai.py
├── assets/
│   └── preview.png
├── README.md
└── requirements.txt
```

---

## How It Works

### Tree Growth

Each branch grows incrementally over time. Once mature, it procedurally spawns child branches using randomized angle and length distributions.

### Environment System

The environment continuously updates:

* weather
* sunlight
* wind
* nutrients
* water
* overall health

These directly affect growth speed and visual appearance.

### Procedural Leaves

Leaves are generated once and stored permanently to prevent flickering and maintain visual consistency.

### Weather Events

Storms can randomly prune branches, allowing the tree to naturally evolve and regrow into new shapes.

---

## Future Improvements

* Branch curvature using Bézier curves
* Seasonal simulation
* Snow and autumn leaves
* Save/load system
* Genetics and evolution system
* Ambient audio
* Shader-based lighting and bloom
* GPU particle systems
* Perlin noise wind simulation

---

## Screenshots

*Add more screenshots here*

```md
![Day](assets/day.png)
![Night](assets/night.png)
![Storm](assets/storm.png)
```

---

## Inspiration

Inspired by:

* bonsai aesthetics
* procedural generation in games
* ecosystem simulations
* generative art
* calm interactive experiences

---

## Learning Goals

This project explores:

* procedural generation
* recursion
* real-time simulation
* animation systems
* game architecture
* environmental systems
* interactive graphics programming

---

## License

MIT License

---

## Author

Prabha Sapkota

• Backend & AI Enthusiast • Creative Developer


  
    
