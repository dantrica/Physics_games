# -*- coding: utf-8 -*-

from pathlib import Path
import subprocess
import sys

carpeta = Path(__file__).resolve().parent
juego = carpeta / "colisiones_OP.py"

if not juego.exists():
    print(f"ERROR: no se encontró {juego}")
    input("Presiona Enter para cerrar...")
    raise SystemExit

comando = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "--noconfirm",
    "--name",
    "Colisiones_OP",
    "--collect-all",
    "pygame",
    str(juego)
]

try:
    subprocess.run(comando, cwd=carpeta, check=True)

    exe = carpeta / "dist" / "Colisiones_OP.exe"

    print("\nEJECUTABLE CREADO CORRECTAMENTE")
    print(f"Ubicación: {exe}")

except subprocess.CalledProcessError as error:
    print("\nERROR AL CREAR EL EJECUTABLE")
    print(f"Código de salida: {error.returncode}")

input("\nPresiona Enter para cerrar...")
