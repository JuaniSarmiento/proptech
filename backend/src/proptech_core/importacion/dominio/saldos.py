"""Validación pura de las hojas `Saldos` y `Control` (design D1, D2, D3, E11 y E14; contrato del
saldo inicial del 4c, E11 y E16). Todo o nada, con todos los errores juntos y cada uno con hoja,
fila, columna y motivo. Sin Excel y sin base: recibe la plantilla ya leída, los identificadores
de las unidades del edificio y la fecha de migración.

Una fila de `Saldos` es de uno de tres tipos (el mismo contrato que `registrar_saldo_inicial`):

- **detalle**: con `Período`; `Vencimiento` y `Concepto` obligatorios;
- **total** único: sin `Período`, `Vencimiento` ni `Concepto`;
- **crédito** a favor: `Importe` negativo, sin `Período`, `Concepto`, `Vencimiento` ni interés. Se
  guarda positivo con `tipo = "credito"`.

Los motivos nunca repiten el valor que escribió la persona.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from proptech_core.compartido.dinero import Dinero, MontoInvalido, sumar
from proptech_core.importacion.dominio.numeros import NumeroInvalido, leer_decimal
from proptech_core.importacion.dominio.plantilla import (
    ENCABEZADOS_POR_HOJA,
    HOJA_CONTROL,
    HOJA_SALDOS,
    ErrorDeImportacion,
    FilaLeida,
    HojaLeida,
    PlantillaLeida,
)

_CERO = Dinero("0.00")
_PERIODO = re.compile(r"(\d{4})-(\d{2})(?:-(\d{2}))?", re.ASCII)
_FECHA_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})", re.ASCII)
_FECHA_CON_BARRAS = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})", re.ASCII)
#: El texto de la plantilla -> el valor de `fila_de_saldo_importada.concepto` y de `componente`.
_CONCEPTOS = {
    "Ordinaria": "ordinaria",
    "Fondo de reserva": "fondo_de_reserva",
    "Extraordinaria": "extraordinaria",
}
_SALDO = "Saldo según el administrador"


@dataclass(frozen=True)
class FilaDeSaldo:
    """Una fila de `Saldos` ya normalizada. `importe` es siempre >= 0: el crédito se guarda positivo
    con `tipo = "credito"`."""

    fila: int
    unidad: str
    tipo: str
    periodo: date | None
    vencimiento: date | None
    concepto: str | None
    importe: Dinero
    interes_acumulado: Dinero


@dataclass(frozen=True)
class FilaDeControl:
    fila: int
    unidad: str
    saldo: Dinero


@dataclass(frozen=True)
class BorradorValidado:
    filas: tuple[FilaDeSaldo, ...]
    controles: tuple[FilaDeControl, ...]


def _error(hoja: str, fila: int | None, columna: str | None, motivo: str) -> ErrorDeImportacion:
    return ErrorDeImportacion(hoja, fila, columna, motivo)


class _Lectora:
    """Lee las celdas de una fila y junta sus errores, en el orden en que se piden."""

    def __init__(self, hoja: str, fila: FilaLeida) -> None:
        self.hoja = hoja
        self.fila = fila
        self.errores: list[ErrorDeImportacion] = []

    def falla(self, columna: str, motivo: str) -> None:
        self.errores.append(_error(self.hoja, self.fila.numero, columna, motivo))

    def texto(self, columna: str) -> str | None:
        """El texto de la celda o `None` si está vacía (o es una fórmula sin valor: ya quedó el
        error de esa columna)."""
        if columna in self.fila.formulas_sin_cache:
            self.falla(
                columna,
                "la celda es una fórmula sin valor guardado: abrí el archivo en Excel y guardalo",
            )
            return None
        valor = self.fila.valores.get(columna)
        return None if valor is None else valor.strip() or None

    def obligatoria(self, columna: str) -> str | None:
        valor = self.texto(columna)
        if valor is None and columna not in self.fila.formulas_sin_cache:
            self.falla(columna, "es obligatoria")
        return valor

    def dinero(self, columna: str, valor: str) -> Dinero | None:
        try:
            numero = leer_decimal(valor, decimales=2, numerico=columna in self.fila.numericas)
            return Dinero(format(numero, "f"))
        except NumeroInvalido as error:
            self.falla(columna, str(error))
        except MontoInvalido:
            self.falla(columna, "es demasiado grande (hasta 999.999.999.999,99)")
        return None

    def unidad(self, unidades: frozenset[str]) -> str | None:
        valor = self.obligatoria("Unidad")
        if valor is None:
            return None
        if valor not in unidades:
            self.falla("Unidad", "no está en el padrón del edificio")
            return None
        return valor


def _fecha(texto: str) -> date | None:
    for patron, orden in ((_FECHA_ISO, (1, 2, 3)), (_FECHA_CON_BARRAS, (3, 2, 1))):
        coincidencia = patron.fullmatch(texto)
        if coincidencia:
            anio, mes, dia = (int(coincidencia[i]) for i in orden)
            try:
                return date(anio, mes, dia)
            except ValueError:
                return None
    return None


def _periodo(texto: str, migracion: date) -> tuple[date | None, str | None]:
    """El primer día del mes, o el motivo por el que no vale."""
    coincidencia = _PERIODO.fullmatch(texto)
    if coincidencia is None:
        return None, "tiene que ser un mes (AAAA-MM) o una fecha con día 1"
    anio, mes = int(coincidencia[1]), int(coincidencia[2])
    if not 1 <= mes <= 12 or anio < 1:
        return None, "no es un mes (AAAA-MM)"
    if coincidencia[3] is not None and int(coincidencia[3]) != 1:
        return None, "si es una fecha, tiene que ser el día 1 del mes"
    periodo = date(anio, mes, 1)
    if periodo > migracion.replace(day=1):
        return None, "es posterior al mes de la migración"
    return periodo, None


@dataclass
class _Leida:
    """Lo que se sabe de una fila de `Saldos` después de leerla, para los chequeos entre filas."""

    fila: int
    unidad: str | None
    #: "detalle", "total" o "credito"; `None` si no se pudo saber (celda de período con fórmula).
    tipo: str | None
    #: Si la celda de `Período` trae algo (decide detalle contra total aunque sea inválido).
    con_periodo: bool
    periodo: date | None = None
    vencimiento: date | None = None
    concepto: str | None = None
    importe: Dinero | None = None
    interes: Dinero = _CERO
    limpia: bool = True


def _leer_fila_de_saldos(
    fila: FilaLeida, unidades: frozenset[str], migracion: date
) -> tuple[_Leida, list[ErrorDeImportacion]]:
    c = _Lectora(HOJA_SALDOS, fila)
    unidad = c.unidad(unidades)
    texto_importe = c.obligatoria("Importe")
    importe = None if texto_importe is None else c.dinero("Importe", texto_importe)
    texto_interes = c.texto("Interés acumulado")
    interes = _CERO
    if texto_interes is not None and (leido := c.dinero("Interés acumulado", texto_interes)):
        interes = leido
        if leido < _CERO:
            c.falla("Interés acumulado", "no puede ser negativo")
    periodo_texto = c.texto("Período")
    vencimiento_texto = c.texto("Vencimiento")
    concepto_texto = c.texto("Concepto")
    con_periodo = periodo_texto is not None
    desconocido = "Período" in fila.formulas_sin_cache
    leida = _Leida(fila.numero, unidad, None, con_periodo, importe=importe, interes=interes)

    if importe is not None and importe < _CERO:
        leida.tipo = "credito"
        if con_periodo:
            c.falla("Período", "el crédito a favor no lleva período")
        if concepto_texto is not None:
            c.falla("Concepto", "el crédito a favor no lleva concepto")
        if vencimiento_texto is not None:
            c.falla("Vencimiento", "el crédito a favor no lleva vencimiento")
        if interes > _CERO:
            c.falla("Interés acumulado", "el crédito a favor no lleva interés")
    elif not desconocido:
        leida.tipo = "detalle" if con_periodo else "total"
        if leida.tipo == "detalle":
            if periodo_texto is not None:
                leida.periodo, motivo = _periodo(periodo_texto, migracion)
                if motivo is not None:
                    c.falla("Período", motivo)
            if vencimiento_texto is None:
                if "Vencimiento" not in fila.formulas_sin_cache:
                    c.falla("Vencimiento", "es obligatorio en una fila con período")
            else:
                fecha = _fecha(vencimiento_texto)
                if fecha is None:
                    c.falla("Vencimiento", "no es una fecha válida (AAAA-MM-DD o DD/MM/AAAA)")
                elif fecha > migracion:
                    c.falla("Vencimiento", "es posterior a la fecha de migración")
                else:
                    leida.vencimiento = fecha
            if concepto_texto is None:
                if "Concepto" not in fila.formulas_sin_cache:
                    c.falla("Concepto", "es obligatorio en una fila con período")
            elif concepto_texto not in _CONCEPTOS:
                opciones = ", ".join(_CONCEPTOS)
                c.falla("Concepto", f"tiene que ser exactamente uno de: {opciones}")
            else:
                leida.concepto = _CONCEPTOS[concepto_texto]
        else:
            if concepto_texto is not None:
                c.falla("Concepto", "el total único no lleva concepto")
            if vencimiento_texto is not None:
                c.falla("Vencimiento", "el total único no lleva vencimiento")
    leida.limpia = not c.errores
    return leida, c.errores


def _chequeos_entre_filas(leidas: list[_Leida]) -> list[ErrorDeImportacion]:
    """Lo que una fila sola no puede saber: la mezcla de modos, el vencimiento de un período y el
    capital 0 de un período (E11 y E16 del 4c)."""
    errores: list[ErrorDeImportacion] = []
    por_unidad: dict[str, list[_Leida]] = {}
    for leida in leidas:
        if leida.unidad is not None:
            por_unidad.setdefault(leida.unidad, []).append(leida)
    for filas in por_unidad.values():
        # Mezcla: el modo de la unidad lo da su primera fila que no es crédito; se marca la
        # primera fila que difiere.
        modos = [f for f in filas if f.tipo in ("detalle", "total")]
        if modos:
            primera = modos[0]
            for otra in modos[1:]:
                if otra.tipo != primera.tipo:
                    errores.append(
                        _error(
                            HOJA_SALDOS,
                            otra.fila,
                            "Período",
                            "la unidad mezcla filas con período y filas sin período (el modo "
                            f"lo fija la fila {primera.fila}): usá un solo modo por unidad",
                        )
                    )
                    break
        # Un período, un vencimiento.
        vencimientos: dict[date, _Leida] = {}
        for f in filas:
            if f.tipo != "detalle" or f.periodo is None or f.vencimiento is None:
                continue
            primera_del_periodo = vencimientos.setdefault(f.periodo, f)
            if f.vencimiento != primera_del_periodo.vencimiento:
                errores.append(
                    _error(
                        HOJA_SALDOS,
                        f.fila,
                        "Vencimiento",
                        "el período ya tiene otro vencimiento en la fila "
                        f"{primera_del_periodo.fila}: las filas de un período vencen el mismo día",
                    )
                )
        # Capital 0: cada período (o el total único) tiene que sumar capital.
        grupos: dict[date | None, list[_Leida]] = {}
        for f in filas:
            if f.tipo == "detalle" and f.periodo is not None:
                grupos.setdefault(f.periodo, []).append(f)
            elif f.tipo == "total":
                grupos.setdefault(None, []).append(f)
        for grupo in grupos.values():
            if not all(f.limpia and f.importe is not None for f in grupo):
                continue
            if sumar(f.importe for f in grupo if f.importe is not None) > _CERO:
                continue
            con_interes = [f for f in grupo if f.interes > _CERO]
            if con_interes:
                errores.append(
                    _error(
                        HOJA_SALDOS,
                        con_interes[0].fila,
                        "Interés acumulado",
                        "el período suma capital 0 y trae interés: no hay deuda sobre la que "
                        "acumularlo",
                    )
                )
            else:
                errores.append(
                    _error(HOJA_SALDOS, grupo[0].fila, "Importe", "el período suma capital 0")
                )
    return errores


def _filas_de_saldo(leidas: list[_Leida]) -> tuple[FilaDeSaldo, ...]:
    resultado = []
    for leida in leidas:
        if leida.unidad is None or leida.importe is None or leida.tipo is None:
            raise ValueError("una fila incompleta no puede llegar al borrador")
        credito = leida.tipo == "credito"
        resultado.append(
            FilaDeSaldo(
                fila=leida.fila,
                unidad=leida.unidad,
                tipo=leida.tipo,
                periodo=leida.periodo,
                vencimiento=leida.vencimiento,
                concepto=leida.concepto,
                importe=-leida.importe if credito else leida.importe,
                interes_acumulado=_CERO if credito else leida.interes,
            )
        )
    return tuple(resultado)


def _leer_control(
    hoja: HojaLeida, unidades: frozenset[str]
) -> tuple[tuple[FilaDeControl, ...], list[ErrorDeImportacion]]:
    errores: list[ErrorDeImportacion] = []
    controles: list[FilaDeControl] = []
    vistas: dict[str, int] = {}
    for fila in hoja.filas:
        c = _Lectora(HOJA_CONTROL, fila)
        unidad = c.unidad(unidades)
        if unidad is not None:
            if unidad in vistas:
                c.falla("Unidad", f"está repetida, ya está en la fila {vistas[unidad]}")
                unidad = None
            else:
                vistas[unidad] = fila.numero
        texto = c.obligatoria(_SALDO)
        saldo = None if texto is None else c.dinero(_SALDO, texto)
        errores.extend(c.errores)
        if unidad is not None and saldo is not None and not c.errores:
            controles.append(FilaDeControl(fila.numero, unidad, saldo))
    return tuple(controles), errores


def _errores_de_archivo(plantilla: PlantillaLeida) -> list[ErrorDeImportacion]:
    errores: list[ErrorDeImportacion] = []
    if HOJA_SALDOS not in plantilla.hojas:
        errores.append(
            _error(
                HOJA_SALDOS,
                None,
                None,
                "falta la hoja Saldos: la hoja Control se usa junto con Saldos",
            )
        )
    if HOJA_CONTROL not in plantilla.hojas:
        errores.append(
            _error(
                HOJA_CONTROL,
                None,
                None,
                "falta la hoja Control: es obligatoria cuando el archivo trae Saldos",
            )
        )
    for nombre in (HOJA_SALDOS, HOJA_CONTROL):
        hoja = plantilla.hojas.get(nombre)
        if hoja is None:
            continue
        errores.extend(
            _error(
                nombre,
                None,
                columna,
                f"falta la columna {columna} en la fila 1 de la hoja {nombre}",
            )
            for columna in ENCABEZADOS_POR_HOJA[nombre]
            if columna not in hoja.encabezados
        )
    return errores


def validar_saldos(
    plantilla: PlantillaLeida, *, unidades: frozenset[str], fecha_de_migracion: date
) -> tuple[BorradorValidado | None, tuple[ErrorDeImportacion, ...]]:
    """`(None, ())` si el archivo no trae saldos (ni `Saldos` ni `Control` tienen filas: así llega
    la plantilla descargada sin completarlos); `(borrador, ())` si son válidos; `(None, errores)`
    con **todos** los errores si no."""
    saldos = plantilla.hojas.get(HOJA_SALDOS)
    control = plantilla.hojas.get(HOJA_CONTROL)
    if not (saldos and saldos.filas) and not (control and control.filas):
        return None, ()
    if (de_archivo := _errores_de_archivo(plantilla)) or saldos is None or control is None:
        return None, tuple(de_archivo)

    errores: list[ErrorDeImportacion] = []
    leidas: list[_Leida] = []
    for fila in saldos.filas:
        leida, de_fila = _leer_fila_de_saldos(fila, unidades, fecha_de_migracion)
        leidas.append(leida)
        errores.extend(de_fila)
    errores.extend(_chequeos_entre_filas(leidas))
    controles, de_control = _leer_control(control, unidades)
    errores.extend(de_control)
    if errores:
        orden = {HOJA_SALDOS: 0, HOJA_CONTROL: 1}
        errores.sort(key=lambda e: (orden.get(e.hoja or "", 2), e.fila or 0))
        return None, tuple(errores)
    return BorradorValidado(_filas_de_saldo(leidas), controles), ()
