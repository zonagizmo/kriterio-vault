"""
Da de alta una instalación autorizada a sincronizar con este servidor.

Se ejecuta a mano en el propio servidor (no existe endpoint HTTP para esto:
no hay ningún usuario "admin" autenticado que pueda dar de alta otras
instalaciones, así que este primer paso — el único que requiere confianza
implícita — se hace por SSH, no por la API).

La clave se muestra una sola vez: solo se guarda su hash (SHA-256) en la
base de datos. Cópiala en el fichero de configuración de la instalación
cliente (variables SYNC_SERVER_URL / SYNC_API_KEY) antes de cerrar la
terminal.

Uso (desde backend/, con el venv activado):
    python scripts/crear_instalacion.py --nombre "PC Oficina" --empresas 1,2
    python scripts/crear_instalacion.py --nombre "PC Juan"          # todas las empresas
"""
import argparse
import hashlib
import secrets
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import SessionLocal, crear_tablas
from app.models.sync import Instalacion


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nombre", required=True, help="Nombre identificativo (ej. 'PC Oficina')")
    parser.add_argument("--empresas", default=None,
                        help="IDs de empresa separados por coma (ej. '1,2'). Omitir = todas.")
    args = parser.parse_args()

    crear_tablas()

    api_key = secrets.token_urlsafe(32)
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    inst_uuid = str(uuid.uuid4())

    db = SessionLocal()
    try:
        inst = Instalacion(
            uuid=inst_uuid,
            nombre=args.nombre,
            api_key_hash=api_key_hash,
            empresas=args.empresas,
        )
        db.add(inst)
        db.commit()
    finally:
        db.close()

    print()
    print("Instalación creada correctamente.")
    print(f"  Nombre:   {args.nombre}")
    print(f"  UUID:     {inst_uuid}")
    print(f"  Empresas: {args.empresas or 'todas'}")
    print()
    print("Clave de API (se muestra UNA SOLA VEZ, no queda guardada en claro):")
    print(f"  {api_key}")
    print()
    print("En la instalación cliente, en backend/.env:")
    print("  SYNC_SERVER_URL=https://kriteriovault.naslive.es")
    print(f"  SYNC_API_KEY={api_key}")
    print()


if __name__ == "__main__":
    main()
