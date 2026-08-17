# Wokwi Browser ESP32 Demo

Online project:

```text
https://wokwi.com/projects/472799587810026497
```

Use the Arduino ESP32 core version in the Wokwi browser editor.

Required files:

- `sketch.ino`
- `embedded_model.h`
- `diagram.json`

Do not add a C file with `app_main()` to this Arduino ESP32 Wokwi project. Arduino already defines `app_main()` internally, so adding a second `app_main()` causes a multiple-definition linker error.

The `diagram.json` file explicitly connects `esp:TX` to `$serialMonitor:RX` and `esp:RX` to `$serialMonitor:TX`. Without these virtual serial connections, the simulation may run while the Serial Monitor remains empty.

Expected serial output:

```text
IoT IDS embedded inference demo
Framework: Arduino ESP32 core
sample=0 expected=normal predicted=normal attack_probability=...
plot_probability:...,plot_predicted:...
```
