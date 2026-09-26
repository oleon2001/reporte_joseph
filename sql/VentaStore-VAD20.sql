-- "Falta en VENTASSTORE pero sí se encuentra en VAD20".
-- Se ejecuta en Central Stellar (VE/GT). Encuentra pagos registrados en
-- VAD20.dbo.MA_PAGOS cuya transacción NO está en VENTASSTORE.dbo.TICKET.
-- Enlace por DocumentUID (se requiere el COLLATE por diferencia de collation
-- entre ambas bases de datos).
-- Parámetros: ? = fecha desde, ? = fecha hasta (yyyy-mm-dd).
SELECT
    mp.c_Sucursal  AS Tienda,
    mp.c_Caja      AS Caja,
    mp.c_Numero    AS TR_EPA,
    mp.DocumentUID AS StellarDocID
FROM VAD20.dbo.MA_PAGOS mp
WHERE CONVERT(date, mp.f_Fecha) BETWEEN ? AND ?
  AND NOT EXISTS (
      SELECT 1 FROM VENTASSTORE.dbo.TICKET t
      WHERE t.DocumentUID COLLATE Modern_Spanish_CI_AS
          = mp.DocumentUID COLLATE Modern_Spanish_CI_AS
  )
