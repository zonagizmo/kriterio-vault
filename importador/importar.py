#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importador de datos desde GestionMGD (DBF) a SQLite/PostgreSQL.

Uso:
    python importar.py --mgd-dir /ruta/a/GestionMGD
    python importar.py --mgd-dir /ruta/a/GestionMGD --empresa MGD018
    python importar.py --mgd-dir /ruta/a/GestionMGD --solo-listar
"""

import sys
import os
import argparse
import datetime
from pathlib import Path

# Añadir el backend al path para usar los modelos
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

try:
    from dbfread import DBF, FieldParser
except ImportError:
    print("ERROR: Instala dbfread con:  pip install dbfread")
    sys.exit(1)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.empresas import Empresa
from app.models.configuracion import (
    Parametro, Actividad, TipoIva, Operacion,
    Referencia, TipoVto, Directo, ExPlantilla,
)
from app.models.contabilidad import (
    Cuenta, Diario, DiarioTxt, Analitica, Ajuste,
    Extra, ExApunte, RefApunte, Lbi,
)
from app.models.clientes_proveedores import (
    Cliente, Proveedor, Vencimiento, Recibo, EtiCod, EtiDat,
)
from app.models.bancos import Banco, MovBanco, Pago
from app.models.facturacion import (
    Familia, FamiliaC, Articulo, ArticuloC,
    FacturaEmitida, FacturaRecibida,
    AlbaranEmitido, AlbaranRecibido,
    Presupuesto, PedidoProveedor, PedidoCliente,
    AlbaranInventario, AlbaranReparto,
    Apunte, Eriva, Foto,
)

_db_default = f"sqlite:///{BACKEND_DIR / 'gestionmgd.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", _db_default)

# Mapeo: nombre de archivo DBF → tabla destino y modelo
TABLAS = {
    "Param":      (Parametro,       "parametros"),
    "Actividad":  (Actividad,       "actividades"),
    "Tipoiva":    (TipoIva,         "tipo_iva"),
    "Tipoop":     (Operacion,       "operaciones"),
    "Tiporef":    (Referencia,      "referencias"),
    "Tipovtos":   (TipoVto,         "tipo_vtos"),
    "Directos":   (Directo,         "directos"),
    "Explant":    (ExPlantilla,     "ex_plantillas"),
    "Cuentas":    (Cuenta,          "cuentas"),
    "Diario":     (Diario,          "diario"),
    "Diatxt":     (DiarioTxt,       "diario_txt"),
    "Analitica":  (Analitica,       "analitica"),
    "Ajustes":    (Ajuste,          "ajustes"),
    "Extra":      (Extra,           "extras"),
    "Exapun":     (ExApunte,        "ex_apuntes"),
    "Tiporefa":   (RefApunte,       "ref_apuntes"),
    "Lbi":        (Lbi,             "lbi"),
    "Clientes":   (Cliente,         "clientes"),
    "Proveed":    (Proveedor,       "proveedores"),
    "Vtos":       (Vencimiento,     "vencimientos"),
    "Recibos":    (Recibo,          "recibos"),
    "ETICOD":     (EtiCod,          "eticod"),
    "ETIDAT":     (EtiDat,          "etidat"),
    "Bancos":     (Banco,           "bancos"),
    "Movbanco":   (MovBanco,        "mov_bancos"),
    "Pagos":      (Pago,            "pagos"),
    "F_fam":      (Familia,         "familias"),
    "F_famc":     (FamiliaC,        "familias_c"),
    "F_art":      (Articulo,        "articulos"),
    "F_artc":     (ArticuloC,       "articulos_c"),
    "Emi":        (FacturaEmitida,  "facturas_emitidas"),
    "Rec":        (FacturaRecibida, "facturas_recibidas"),
    "F_albemi":   (AlbaranEmitido,  "albaranes_emitidos"),
    "F_albrec":   (AlbaranRecibido, "albaranes_recibidos"),
    "F_albpre":   (Presupuesto,     "presupuestos"),
    "F_albped":   (PedidoProveedor, "pedidos_proveedor"),
    "F_albpede":  (PedidoCliente,   "pedidos_cliente"),
    "F_albinv":   (AlbaranInventario, "albaranes_inventario"),
    "F_albrep":   (AlbaranReparto,  "albaranes_reparto"),
    "F_apu":      (Apunte,          "apuntes"),
    "Eriva":      (Eriva,           "eriva"),
    "Fotos":      (Foto,            "fotos"),
}

# Mapeo de campos DBF → columnas del modelo (solo los que difieren de nombre)
CAMPO_MAP = {
    Parametro:       {"ETIQUETA": "etiqueta", "TEXTO": "texto", "MAS": "mas"},
    Actividad:       {"NUMERO": "numero", "NOMBRE": "nombre", "ETIQUETA": "etiqueta", "ACTIVA": "activa"},
    TipoIva:         {"TIPO": "tipo", "NUMERO": "numero", "TEXTO": "texto", "IVA": "iva",
                      "CTA_IVA": "cta_iva", "IVA_RE": "iva_re", "CTA_IVA_RE": "cta_iva_re",
                      "PORDEFECTO": "pordefecto", "INACTIVO": "inactivo", "ABREVIA": "abrevia"},
    Operacion:       {"TIPO": "tipo", "NUMERO": "numero", "TEXTO": "texto", "CUENTA": "cuenta",
                      "PORDEFECTO": "pordefecto", "IVA": "iva"},
    Referencia:      {"TIPO": "tipo", "NUMERO": "numero", "TEXTO": "texto"},
    TipoVto:         {"NUMERO": "numero", "TEXTO": "texto", "CLIDEF": "clidef",
                      "PROVDEF": "provdef", "ESTADO": "estado"},
    Directo:         {"CUENTA": "cuenta", "TEXTO": "texto"},
    ExPlantilla:     {"TEXTO": "texto", "CONTENIDO": "contenido"},
    Cuenta:          {"CUENTA": "cuenta", "TEXTO": "texto", "DEBE": "debe", "HABER": "haber",
                      "PENTIDAD": "pentidad", "PDIRECTO": "pdirecto", "PTIPO": "ptipo", "MARCA": "marca"},
    Diario:          {"ASIENTO": "asiento", "FECHA": "fecha", "TPASIENTO": "tpasiento",
                      "CLAVE": "clave", "CLAVE_ORI": "clave_ori", "TIPO": "tipo",
                      "NUMERO": "numero", "IMPORTE": "importe", "CUENTA": "cuenta",
                      "SALDO": "saldo", "MULTI": "multi", "MARCA": "marca"},
    DiarioTxt:       {"TIPO": "tipo", "NUMERO": "numero", "CUENTA": "cuenta", "TEXTO": "texto",
                      "DOCU": "docu", "MULTI": "multi", "NEGATIVO": "negativo",
                      "ACUMULAR": "acumular", "FECHA": "fecha", "NOTAS": "notas"},
    Analitica:       {"TIPO": "tipo", "NUMERO": "numero", "CUENTA": "cuenta",
                      "ACTIVIDAD": "actividad", "IMPORTE": "importe"},
    Ajuste:          {"TIPO": "tipo", "NUMERO": "numero", "CUENTA": "cuenta",
                      "IMPORTE": "importe", "CONTRA": "contra", "CAMBIOAS": "cambioas",
                      "AFECTAIVA": "afectaiva", "DECLTERC": "declterc"},
    Extra:           {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "TIPO": "tipo",
                      "CLAVE": "clave", "TEXTO": "texto", "GRUPO": "grupo",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    ExApunte:        {"NUMERO": "numero", "EXTRA": "extra", "CUENTA": "cuenta",
                      "AYUDA": "ayuda", "DH": "dh", "IMPORTE": "importe", "DECLTERC": "declterc"},
    RefApunte:       {"TIPO": "tipo", "NUMERO": "numero", "TPNUMERO": "tpnumero"},
    Lbi:             {"NOMBRE": "nombre", "CUENBIEN": "cuenbien", "CUENDOTA": "cuendota",
                      "CUENAMORT": "cuenamort", "COSTE": "coste", "RESIDUAL": "residual",
                      "FECHA": "fecha", "FBAJA": "fbaja", "CBAJA": "cbaja",
                      "COEFI": "coefi", "PERIODO": "periodo", "MESES": "meses",
                      "IVA": "iva", "MARCA": "marca", "RECIBIDA": "recibida",
                      "PROVEEDOR": "proveedor", "REGFECHA": "regfecha",
                      "REGISTRO": "registro", "CUADRO": "cuadro", "NOTAS": "notas"},
    Cliente:         {"NUMERO": "numero", "NOMBRE": "nombre", "COMERCIAL": "comercial",
                      "DOMICILIO": "domicilio", "LOCALIDAD": "localidad", "PROVINCIA": "provincia",
                      "COD_POSTAL": "cod_postal", "AP_CORREOS": "ap_correos", "NIF": "nif",
                      "CUENTA": "cuenta", "OPERACION": "operacion", "BRUTO": "bruto",
                      "NETO": "neto", "PENDIENTE": "pendiente", "BANCO_NOM": "banco_nom",
                      "BANCO_SUC": "banco_suc", "BANCO_DIG": "banco_dig", "IVA": "iva",
                      "BANCO_TIT": "banco_tit", "ANTICIPO": "anticipo", "TIPO": "tipo",
                      "DECLTERC": "declterc", "MARCA": "marca",
                      "CONTACTOS": "contactos", "NOTAS": "notas"},
    Proveedor:       {"NUMERO": "numero", "NOMBRE": "nombre", "COMERCIAL": "comercial",
                      "DOMICILIO": "domicilio", "LOCALIDAD": "localidad", "PROVINCIA": "provincia",
                      "COD_POSTAL": "cod_postal", "AP_CORREOS": "ap_correos", "NIF": "nif",
                      "CUENTA": "cuenta", "OPERACION": "operacion", "BRUTO": "bruto",
                      "PENDIENTE": "pendiente", "NETO": "neto", "IVA": "iva",
                      "CTAIRPF": "ctairpf", "ANTICIPO": "anticipo", "TIPO": "tipo",
                      "CCAJA": "ccaja", "DECLTERC": "declterc", "MARCA": "marca",
                      "CONTACTOS": "contactos", "NOTAS": "notas"},
    Vencimiento:     {"NUMERO": "numero", "TIPO": "tipo", "TPNUMERO": "tpnumero",
                      "FECHA": "fecha", "IMPORTE": "importe", "PENDIENTE": "pendiente",
                      "CUENTA": "cuenta", "CUENTADEF": "cuentadef",
                      "PENTIDAD": "pentidad", "PTIPO": "ptipo"},
    Recibo:          {"TIPO": "tipo", "AGENTE": "agente", "TIPOAP": "tipoap",
                      "DIA": "dia", "MES": "mes", "EJERCICIO": "ejercicio",
                      "IMPORTE": "importe", "CONCEPTO": "concepto",
                      "RSEPARADO": "rseparado", "VTO": "vto"},
    EtiCod:          {"TIPO": "tipo", "CLAVE": "clave", "FORMA": "forma", "CODIGO": "codigo"},
    EtiDat:          {"TIPO": "tipo", "NUMERO": "numero", "CLAVE": "clave", "TEXTO": "texto"},
    Banco:           {"NUMERO": "numero", "NOMBRE": "nombre", "SUCURSAL": "sucursal",
                      "NUMCTA": "numcta", "CUENTA": "cuenta", "SALDOINI": "saldoini",
                      "SALDOACT": "saldoact", "NOTAS": "notas"},
    MovBanco:        {"BANCO": "banco", "NUMERO": "numero", "CNUMERO": "cnumero",
                      "TIPONUM": "tiponum", "CNUMALT": "cnumalt", "TEXTO": "texto",
                      "AUTOTEXT": "autotext", "CLAVE": "clave", "FECHA": "fecha",
                      "TOTAL": "total", "SALDONUE": "saldonue", "ESTADO": "estado",
                      "MARCA": "marca", "NOTAS": "notas"},
    Pago:            {"BANCO": "banco", "NUMERO": "numero", "IMPORTE": "importe",
                      "VTO": "vto", "DIRSUBCTA": "dirsubcta", "NUMEROT": "numerot",
                      "BANCOT": "bancot", "DECLTERC": "declterc"},
    Familia:         {"NUMERO": "numero", "PADRE": "padre", "TEXTO": "texto",
                      "DCTO": "dcto", "TDCTO": "tdcto"},
    FamiliaC:        {"FAMILIA": "familia", "CARNUM": "carnum", "TIPO": "tipo", "TEXTO": "texto"},
    Articulo:        {"NUMERO": "numero", "CODIGO": "codigo", "EAN13": "ean13",
                      "UBICACION": "ubicacion", "PROVEEDOR": "proveedor", "FAMILIA": "familia",
                      "NOMBRE": "nombre", "PVENTA": "pventa", "DCTO": "dcto", "TDCTO": "tdcto",
                      "DCTO2": "dcto2", "DCTO3": "dcto3", "PCOMPRA": "pcompra",
                      "PCDCTO": "pcdcto", "PCDCTO2": "pcdcto2", "PCDCTO3": "pcdcto3",
                      "TIPOIVAC": "tipoivac", "TIPOIVAV": "tipoivav",
                      "OPERACIONC": "operacionc", "OPERACIONV": "operacionv",
                      "ALBINVENT": "albinvent", "FINVENT": "finvent",
                      "QINVENT": "qinvent", "QCOMPRAS": "qcompras", "QVENTAS": "qventas",
                      "MINIMO": "minimo", "TIPO": "tipo", "MARCA": "marca",
                      "ASOCIADO": "asociado", "NOTAS": "notas"},
    ArticuloC:       {"ARTICULO": "articulo", "CARNUM": "carnum", "DATO": "dato"},
    FacturaEmitida:  {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "FREGISTRO": "fregistro",
                      "CLIENTE": "cliente", "CLCUENTA": "clcuenta", "TIPOOP": "tipoop",
                      "TOCUENTA": "tocuenta", "TOTAL": "total", "TOTALDECL": "totaldecl",
                      "DECLTERC": "declterc", "CCAJA": "ccaja", "ESTADO": "estado",
                      "MARCA": "marca", "REGISTRO": "registro", "NOTAS": "notas"},
    FacturaRecibida: {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "REGFECHA": "regfecha",
                      "PROVEEDOR": "proveedor", "PRCUENTA": "prcuenta",
                      "PRFACTURA": "prfactura", "PRFECHA": "prfecha",
                      "TIPOOP": "tipoop", "TOCUENTA": "tocuenta", "TOTAL": "total",
                      "TOTALDECL": "totaldecl", "DECLTERC": "declterc", "CCAJA": "ccaja",
                      "ESTADO": "estado", "MARCA": "marca", "REGISTRO": "registro",
                      "NOTAS": "notas"},
    AlbaranEmitido:  {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "CLIENTE": "cliente",
                      "FACTURA": "factura", "IMPORTE": "importe", "APUNTES": "apuntes",
                      "CPI": "cpi", "ORDEN": "orden", "ESTADOREP": "estadorep",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    AlbaranRecibido: {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "PROVEEDOR": "proveedor",
                      "FACTURA": "factura", "PRALBARAN": "pralbaran", "PRFECHA": "prfecha",
                      "IMPORTE": "importe", "APUNTES": "apuntes", "CPI": "cpi",
                      "ORDEN": "orden", "ESTADOREP": "estadorep", "PEDIDO": "pedido",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    Presupuesto:     {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "CLIENTE": "cliente",
                      "IMPORTE": "importe", "APUNTES": "apuntes",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    PedidoProveedor: {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "PROVEEDOR": "proveedor",
                      "IMPORTE": "importe", "APUNTES": "apuntes",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    PedidoCliente:   {"NUMERO": "numero", "CNUMERO": "cnumero", "TIPONUM": "tiponum",
                      "CNUMALT": "cnumalt", "FECHA": "fecha", "CLIENTE": "cliente",
                      "IMPORTE": "importe", "APUNTES": "apuntes",
                      "ESTADO": "estado", "MARCA": "marca", "NOTAS": "notas"},
    AlbaranInventario: {"NUMERO": "numero", "TIPO": "tipo", "CNUMERO": "cnumero",
                        "TIPONUM": "tiponum", "CNUMALT": "cnumalt", "FECHA": "fecha",
                        "APUNTES": "apuntes", "MARCA": "marca", "NOTAS": "notas"},
    AlbaranReparto:  {"TIPO": "tipo", "ALBARAN": "albaran", "FACTURA": "factura",
                      "IMPORTE": "importe", "APUNTES": "apuntes", "CPI": "cpi",
                      "ORDEN": "orden", "REPARTO": "reparto"},
    Apunte:          {"ALBARAN": "albaran", "TALBARAN": "talbaran", "FECHA": "fecha",
                      "TIPO": "tipo", "ARTICULO": "articulo", "TEXTO": "texto",
                      "TEXTO2": "texto2", "DCTO1": "dcto1", "DCTO2": "dcto2",
                      "DCTO3": "dcto3", "CANTIDAD": "cantidad", "PRECIO": "precio",
                      "IMPORTE": "importe", "TIVA": "tiva", "TIPOOP": "tipoop",
                      "CUENTA": "cuenta", "REPARTO": "reparto", "GRUPO": "grupo",
                      "ALMACEN": "almacen"},
    Eriva:           {"TIPO": "tipo", "FACTURA": "factura", "NUMERO": "numero",
                      "IVA": "iva", "IVA_CTA": "iva_cta", "IVA_TOTAL": "iva_total",
                      "RE": "re", "RE_CTA": "re_cta", "RE_TOTAL": "re_total",
                      "BASE": "base", "NODEDU": "nodedu", "BINVERSION": "binversion"},
    Foto:            {"TIPO": "tipo", "NUMERO": "numero", "NOMBRE": "nombre",
                      "MOSTRAR": "mostrar", "IZQ": "izq", "ARR": "arr",
                      "ANCHO": "ancho", "ALTO": "alto"},
}


def limpiar_valor(valor):
    """Convierte valores DBF al tipo correcto para PostgreSQL."""
    if valor is None:
        return None
    if isinstance(valor, str):
        v = valor.strip()
        return v if v else None
    if isinstance(valor, datetime.datetime):
        return valor.date()
    return valor


def leer_dbf(ruta: Path, encoding: str = "latin-1"):
    """Lee un archivo DBF y devuelve una lista de diccionarios."""
    try:
        tabla = DBF(str(ruta), encoding=encoding, ignore_missing_memofile=True)
        return [dict(rec) for rec in tabla]
    except Exception as e:
        print(f"  AVISO: no se pudo leer {ruta.name}: {e}")
        return []


def buscar_dbf(carpeta: Path, nombre_base: str) -> Path | None:
    """Busca el archivo DBF con ese nombre (sin distinguir mayúsculas)."""
    for f in carpeta.iterdir():
        if f.suffix.lower() == ".dbf" and f.stem.lower() == nombre_base.lower():
            return f
    return None


def importar_empresa(session, empresa: Empresa, carpeta: Path):
    """Importa todos los datos de una empresa desde su carpeta DBF."""
    print(f"\n  Importando {empresa.codigo} desde {carpeta.name}...")

    for nombre_dbf, (modelo, tabla_nombre) in TABLAS.items():
        ruta = buscar_dbf(carpeta, nombre_dbf)
        if not ruta:
            continue

        registros = leer_dbf(ruta)
        if not registros:
            continue

        campo_map = CAMPO_MAP.get(modelo, {})
        insertados = 0

        for reg in registros:
            kwargs = {"empresa_id": empresa.id}
            for campo_dbf, campo_modelo in campo_map.items():
                if campo_dbf in reg:
                    kwargs[campo_modelo] = limpiar_valor(reg[campo_dbf])

            if len(kwargs) > 1:
                session.add(modelo(**kwargs))
                insertados += 1

        if insertados:
            session.flush()
            print(f"    {tabla_nombre}: {insertados} registros")

    session.commit()


def _nombres_empresas(mgd_dir: Path) -> dict:
    """Lee nombres de empresa desde Comun/Empresas.dbf (clave: numero → nombre)."""
    nombres = {}
    comun_dbf = mgd_dir / "Comun" / "Empresas.dbf"
    if comun_dbf.exists():
        try:
            for r in DBF(str(comun_dbf), encoding="latin-1", ignore_missing_memofile=True):
                num = r.get("NUMERO")
                nom = str(r.get("NOMBRE", "")).strip()
                if num and nom:
                    nombres[int(num)] = nom
        except Exception:
            pass
    return nombres


def listar_empresas(mgd_dir: Path):
    """Lista las carpetas de empresa encontradas."""
    nombres = _nombres_empresas(mgd_dir)
    print(f"\nEmpresas encontradas en {mgd_dir}:\n")
    print(f"  {'Código':<10}  {'Nombre':<45}  DBFs")
    print(f"  {'-'*10}  {'-'*45}  ----")
    for d in sorted(mgd_dir.iterdir()):
        if d.is_dir() and (d.name.upper().startswith("MGD") or d.name.lower() == "mgd997"):
            try:
                num = int(d.name.upper().replace("MGD", "")) if d.name.upper().startswith("MGD") else 997
            except ValueError:
                num = 0
            nombre = nombres.get(num, "—")
            n_dbf = len(list(d.glob("*.dbf"))) + len(list(d.glob("*.DBF")))
            print(f"  {d.name:<10}  {nombre:<45}  {n_dbf}")


def main():
    parser = argparse.ArgumentParser(description="Importa datos de GestionMGD (DBF) a PostgreSQL")
    parser.add_argument("--mgd-dir", required=True, help="Ruta a la carpeta GestionMGD")
    parser.add_argument("--empresa", help="Código de empresa a importar (ej: MGD004). Si no se indica, importa todas.")
    parser.add_argument("--solo-listar", action="store_true", help="Solo lista las empresas, no importa")
    parser.add_argument("--borrar-antes", action="store_true", help="Borra los datos existentes antes de importar")
    args = parser.parse_args()

    mgd_dir = Path(args.mgd_dir)
    if not mgd_dir.exists():
        print(f"ERROR: No existe la carpeta {mgd_dir}")
        sys.exit(1)

    if args.solo_listar:
        listar_empresas(mgd_dir)
        return

    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    carpetas_empresa = sorted([
        d for d in mgd_dir.iterdir()
        if d.is_dir() and (d.name.upper().startswith("MGD") or d.name.lower() == "mgd997")
    ])

    if args.empresa:
        carpetas_empresa = [d for d in carpetas_empresa if d.name.upper() == args.empresa.upper()]
        if not carpetas_empresa:
            print(f"ERROR: No se encontró la empresa {args.empresa}")
            sys.exit(1)

    if args.borrar_antes:
        codigos = [d.name for d in carpetas_empresa]
        empresas_existentes = session.query(Empresa).filter(Empresa.codigo.in_(codigos)).all()
        for emp in empresas_existentes:
            print(f"Borrando datos de {emp.codigo}...")
            for modelo, _ in TABLAS.values():
                session.query(modelo).filter_by(empresa_id=emp.id).delete()
            session.delete(emp)
        session.commit()

    print(f"\nImportando {len(carpetas_empresa)} empresa(s)...")

    nombres = _nombres_empresas(mgd_dir)

    for carpeta in carpetas_empresa:
        try:
            num = int(carpeta.name.upper().replace("MGD", "")) if carpeta.name.upper().startswith("MGD") else 997
        except ValueError:
            num = 0
        nombre = nombres.get(num, carpeta.name)

        empresa = session.query(Empresa).filter_by(codigo=carpeta.name).first()
        if not empresa:
            empresa = Empresa(codigo=carpeta.name, nombre=nombre, activa=True)
            session.add(empresa)
            session.flush()
        else:
            empresa.nombre = nombre

        importar_empresa(session, empresa, carpeta)

    session.close()
    print("\nImportación completada.")


if __name__ == "__main__":
    main()
