"""
Corrige vencimientos tipo 'X' (extras) cuyo campo tpnumero quedó mal enlazado
durante la migración desde el sistema antiguo.

Diagnóstico (sesión 2026-07-21): en el sistema antiguo, Vencimiento.TPNUMERO
guardaba el número de línea de apunte (un contador global, equivalente a
ex_apuntes.numero), no el número de documento del extra. El importador
(importador/importar.py) copió ese campo tal cual a la columna `tpnumero`,
que el código actual interpreta como "número de extra". Resultado: cientos
de vencimientos migrados apuntan al extra equivocado (o a uno inexistente).

Método de corrección: para cada vencimiento tipo X, se busca en ex_apuntes
la línea cuyo numero == tpnumero actual. Si esa línea encaja exactamente en
cuenta e importe (en valor absoluto) con el vencimiento, su campo `extra` es
el verdadero número de extra al que pertenece el vencimiento.

Solo se corrigen los casos con una única línea de apunte candidata que
encaje perfectamente. Todo lo demás (0 candidatos, candidatos ambiguos, o ya
correcto) se dejan intactos y se listan para revisión manual.

Uso:
    python fix_tpnumero_extras.py            # solo analiza y muestra el informe (no toca la BD)
    python fix_tpnumero_extras.py --apply     # aplica los cambios confirmados, con backup previo
"""
import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "gestionmgd.db"
BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups"
TOLERANCIA_IMPORTE = 0.005


def analizar(con):
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    correcciones = []   # (empresa, vto_id, vto_numero, tpnumero_actual, tpnumero_nuevo, cuenta, importe, fecha)
    sin_resolver = []   # (empresa, vto_id, vto_numero, tpnumero_actual, motivo)

    for empresa in (1, 2):
        cur.execute("SELECT * FROM vencimientos WHERE empresa_id=? AND tipo='X'", (empresa,))
        vtos = cur.fetchall()

        for v in vtos:
            cuenta = v["cuentadef"]
            importe = v["importe"]
            tpnumero = v["tpnumero"]

            if cuenta is None or importe is None:
                sin_resolver.append((empresa, v["id"], v["numero"], tpnumero, "cuenta/importe nulos"))
                continue

            # ¿ya está bien enlazado? (el propio extra tpnumero tiene una línea de asiento que encaja)
            cur.execute(
                """
                SELECT 1 FROM diario
                WHERE empresa_id=? AND tipo='X' AND numero=? AND cuenta=?
                AND ABS(ABS(importe) - ABS(?)) < ?
                """,
                (empresa, tpnumero, cuenta, importe, TOLERANCIA_IMPORTE),
            )
            if cur.fetchone():
                continue  # ya correcto, no tocar

            # Blindaje: si tpnumero apunta a un extra CREADO DESDE LA APP (no migrado,
            # cnumero IS NULL), create_extra garantiza tpnumero=extra.numero al crearlo,
            # así que ese vencimiento SIEMPRE fue el suyo propio -- salvo que el mismo
            # extra tenga OTRO vencimiento que sí encaje perfectamente con su asiento
            # (caso real: extra 389 tiene el vto 833, que cuadra exacto, y el 394, que
            # es un intruso migrado que solo coincide en número). Sin ese "hermano" que
            # demuestre cuál es el legítimo, no hay forma fiable de distinguir un
            # vto legítimo con cuenta distinta a propósito de uno realmente erróneo,
            # así que se protege y no se toca.
            cur.execute(
                "SELECT cnumero FROM extras WHERE empresa_id=? AND numero=?", (empresa, tpnumero)
            )
            extra_actual = cur.fetchone()
            if extra_actual is not None and extra_actual["cnumero"] is None:
                # El hermano cuenta como "legítimo confirmado" si su cuenta encaja con el
                # asiento (caso normal), o si no tiene cuenta rellenada pero el importe sí
                # coincide exactamente (cuentadef es opcional al crear el extra; un campo
                # vacío no puede "no cuadrar", así que no debe descartar al hermano).
                cur.execute(
                    """
                    SELECT 1 FROM vencimientos v2
                    JOIN diario d ON d.empresa_id=v2.empresa_id AND d.tipo='X' AND d.numero=v2.tpnumero
                        AND (d.cuenta=v2.cuentadef OR v2.cuentadef IS NULL)
                        AND ABS(ABS(d.importe) - ABS(v2.importe)) < ?
                    WHERE v2.empresa_id=? AND v2.tipo='X' AND v2.tpnumero=? AND v2.id!=?
                    """,
                    (TOLERANCIA_IMPORTE, empresa, tpnumero, v["id"]),
                )
                if not cur.fetchone():
                    continue  # sin hermano confirmado legítimo -> se protege, no se toca

            # buscar la línea de apunte que decodifica el verdadero extra
            cur.execute(
                "SELECT extra, cuenta, importe FROM ex_apuntes WHERE empresa_id=? AND numero=?",
                (empresa, tpnumero),
            )
            candidatos = [
                r for r in cur.fetchall()
                if r["cuenta"] == cuenta and abs(abs(r["importe"]) - abs(importe)) < TOLERANCIA_IMPORTE
            ]

            if len(candidatos) == 1:
                extra_real = candidatos[0]["extra"]
                cur.execute(
                    "SELECT 1 FROM extras WHERE empresa_id=? AND numero=?", (empresa, extra_real)
                )
                if not cur.fetchone():
                    sin_resolver.append(
                        (empresa, v["id"], v["numero"], tpnumero, f"extra decodificado {extra_real} no existe")
                    )
                    continue
                correcciones.append(
                    (empresa, v["id"], v["numero"], tpnumero, extra_real, cuenta, importe, v["fecha"])
                )
            elif len(candidatos) == 0:
                sin_resolver.append(
                    (empresa, v["id"], v["numero"], tpnumero, "sin línea de apunte candidata")
                )
            else:
                sin_resolver.append(
                    (empresa, v["id"], v["numero"], tpnumero, f"{len(candidatos)} candidatos ambiguos")
                )

    return correcciones, sin_resolver


def imprimir_informe(correcciones, sin_resolver):
    print(f"\n{'='*70}\nINFORME DE ANÁLISIS\n{'='*70}")
    for empresa in (1, 2):
        c = [x for x in correcciones if x[0] == empresa]
        s = [x for x in sin_resolver if x[0] == empresa]
        print(f"\nEmpresa {empresa}:")
        print(f"  Correcciones propuestas: {len(c)}")
        print(f"  Sin resolver (no se tocan): {len(s)}")

    print(f"\nTotal correcciones propuestas: {len(correcciones)}")
    print(f"Total sin resolver: {len(sin_resolver)}")

    if correcciones:
        print(f"\n{'-'*70}\nDetalle de correcciones (primeras 30):\n{'-'*70}")
        for empresa, vto_id, vto_num, viejo, nuevo, cuenta, importe, fecha in correcciones[:30]:
            print(f"  empresa={empresa} vto_id={vto_id} vto_num={vto_num} "
                  f"tpnumero {viejo} -> {nuevo}  (cuenta={cuenta} importe={importe} fecha={fecha})")
        if len(correcciones) > 30:
            print(f"  ... y {len(correcciones) - 30} más")

    if sin_resolver:
        print(f"\n{'-'*70}\nSin resolver, requieren revisión manual (primeras 20):\n{'-'*70}")
        for empresa, vto_id, vto_num, viejo, motivo in sin_resolver[:20]:
            print(f"  empresa={empresa} vto_id={vto_id} vto_num={vto_num} tpnumero={viejo}  motivo: {motivo}")
        if len(sin_resolver) > 20:
            print(f"  ... y {len(sin_resolver) - 20} más")


def hacer_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    ahora = datetime.now().strftime("%Y-%m-%d_%H-%M")
    destino = BACKUP_DIR / f"gestionmgd_pre-fix-tpnumero-extras_{ahora}.db"
    shutil.copy2(DB_PATH, destino)
    print(f"\nBackup creado: {destino}")
    return destino


def aplicar(con, correcciones):
    cur = con.cursor()
    for empresa, vto_id, vto_num, viejo, nuevo, cuenta, importe, fecha in correcciones:
        cur.execute("UPDATE vencimientos SET tpnumero=? WHERE id=?", (nuevo, vto_id))
    con.commit()
    print(f"\n{len(correcciones)} vencimientos actualizados y confirmados (commit).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="Aplica los cambios (por defecto solo analiza, no toca la BD)")
    args = parser.parse_args()

    con = sqlite3.connect(DB_PATH)
    try:
        correcciones, sin_resolver = analizar(con)
        imprimir_informe(correcciones, sin_resolver)

        if not args.apply:
            print("\n(Modo análisis: no se ha modificado la base de datos. "
                  "Ejecuta con --apply para aplicar las correcciones.)")
            return

        if not correcciones:
            print("\nNo hay correcciones que aplicar.")
            return

        hacer_backup()
        aplicar(con, correcciones)
    finally:
        con.close()


if __name__ == "__main__":
    main()
