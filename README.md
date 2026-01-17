

# Digital Bonsai 🌱

A procedural **Digital Bonsai tree simulation** built using Python Turtle.
The project focuses on **organic branch generation**, **leaf physics**, and a **lightweight animation loop**, with planned expansion toward interactivity and environmental systems.

---

## Overview

**Digital Bonsai** simulates the growth and behavior of a miniature tree using recursive algorithms and simplified physics.
It renders a carefully shaped bonsai structure with a dense canopy of static leaves, alongside dynamically falling leaves affected by wind and gravity.

The codebase is designed to evolve into an **interactive bonsai simulator**, supporting pruning, weather effects, and seasonal transitions.

---

## Features

### Implemented

* Procedural bonsai-style trunk and branch generation
* Recursive branching with controlled curvature
* Static canopy leaf placement at branch endpoints
* Dynamic falling leaves with:

  * Gravity
  * Wind oscillation
  * Rotation and damping
* Ground collision and settling
* Optimized rendering (static vs dynamic layers)
* Stable 60 FPS animation loop

### Physics Model

* Sinusoidal wind force
* Velocity damping for natural motion
* Ground collision handling
* Randomized turbulence for realism

---

## Architecture

### Rendering Strategy

* Static elements (tree, ground, canopy leaves) are drawn once
* Dynamic elements (falling leaves) are updated every frame
* Uses non-blocking `ontimer()` animation scheduling

### Core Components

* `draw_trunk()` – Curved trunk formation
* `draw_branch()` – Recursive bonsai branching
* `Leaf` class – Leaf physics and rendering
* `animate()` – Main simulation loop

---

## Technology Stack

* Python 3.13+
* turtle (2D rendering & animation)
* math (trigonometry & oscillation)
* random (organic variation)
* time (frame timing)

> **Note:** `pygame` is currently imported but not yet active.
> It is reserved for future real-time input and performance upgrades.

---

## Installation & Usage

```bash
git clone https://github.com/prrabhagit/digital-bonsai.git
cd digital-bonsai
python digital_bonsai.py
```

No external dependencies required.

---

## Planned Enhancements

###  Interaction

* Keyboard-based pruning (branch trimming)
* Manual leaf shedding
* Tree reset and regeneration

###  Environment

* Dynamic wind intensity
* Storm and calm modes
* Rain-influenced gravity
* Seasonal leaf color transitions

###  Growth System

* Time-based growth stages
* Branch regeneration after pruning
* Aging and shaping mechanics

###  Engine Upgrade

* Migration to Pygame
* Improved input handling
* Higher frame rates
* Particle-based effects

---

## Design Philosophy

Digital Bonsai emphasizes:

* Controlled minimalism
* Organic imperfection
* Algorithmic growth over realism
* Expandability over complexity

---

## Project Status

**Active development**
Core simulation complete, interactive systems planned.

---


## Author

**Prabha**
Engineering Student
Creative Coding | Simulations | Systems Design

---


  
    
