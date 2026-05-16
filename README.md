

#  Digital Bonsai — Simulation

A highly detailed **procedural bonsai tree ecosystem simulator** built with Python and Arcade.
This project simulates not just a growing tree, but an entire **living environment system** with realistic weather, seasons, plant physiology, and interactive pruning mechanics.

---

##  Features

###  Realistic Tree Growth

* Apical dominance (top growth stronger than side branches)
* Gravitropism (branches naturally bend toward horizontal)
* Pipe-model thickness simulation
* Dormant buds & apical release after pruning
* Branch healing with **callus formation**
* Leaf-level seasonal color transitions

###  Dynamic Weather System

* Sunny, cloudy, rainy, stormy, foggy conditions
* Pressure-based weather transitions
* Wind gust simulation
* Realistic clouds, fog, rain streaks, and snowflakes

###  Seasonal Ecosystem

* Full **spring → summer → autumn → winter cycle**
* Temperature and frost simulation
* Seasonal growth rate changes
* Autumn leaf color transformation

###  Interactive Bonsai Care

* Watering and fertilizing system
* Click-to-prune branches
* Real-time healing (wound callus formation)
* Tree responds dynamically to pruning stress

###  Environmental Simulation

* Soil moisture, nutrients, humidity
* Evapotranspiration system
* Day/night cycle with sky gradient changes
* Health-based growth model

###  UI & Experience

* Live HUD showing tree stats
* Pause / speed control
* Weather override keys
* Notification system
* Smooth animations and visual effects

---

##  Core Simulation Concepts

This project combines multiple biological and physical models:

* **Plant physiology simulation**
* **Environmental feedback loops**
* **Procedural geometry (recursive branching tree)**
* **Resource-driven growth system**
* **Agent-based environmental particles (rain, snow, fog)**

---

##  Controls

### Care Actions

* **W** → Water tree
* **F** → Fertilize

### Simulation Control

* **P** → Pause / Resume
* **Space** → Reset speed (x1)
* **[** → Slow simulation
* **]** → Speed up simulation

### Time Control

* **T** → +1 hour
* **N** → Next day
* **S** → Next season

### Weather Override

* **1** → Sunny
* **2** → Cloudy
* **3** → Rainy
* **4** → Stormy
* **5** → Foggy

### Other

* **Left Click** → Prune branch
* **R** → Reset simulation
* **ESC** → Quit

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/prrabhagit/digital-bonsai.git
cd digital-bonsai
```

### 2. Install dependencies

```bash
pip install arcade
```

### 3. Run the simulation

```bash
python bonsai.py
```

---

##  Requirements

* Python 3.8+
* Arcade library

Install Arcade:

```bash
pip install arcade
```

---

##  Project Structure

```
digital-bonsai/
│
├── bonsai.py        # Full simulation engine
├── README.md
├── requirements.txt
├── 
      # Documentation
```

---

## Future Improvements

* Soil microbiome simulation
* Species-specific bonsai behaviors
* Save/load tree states
* Camera zoom & pan system
* Audio (wind, rain, ambient nature)
* AI bonsai stylist mode
* Growth replay system (time-lapse export)

---

##  Preview



##  Author

Built using Python and Arcade

-Prabha Sapkota | Backend dev | AI enthusiast
---

##  License

This project is open-source and available under the MIT License.

---
