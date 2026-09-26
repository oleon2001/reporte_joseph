-- Anomalía 1 (GT, AS400 Central): NO LLEGÓ CLIENTE A MAECEC (cliente de transacción).
-- Parámetro: ? = días hacia atrás (por defecto 5).
SELECT a.TDACMV AS Tienda, a.CAJCMV AS Caja, a.TRSCMV AS TR_EPA
FROM ventas.trcmov a
EXCEPTION JOIN ventas.MAECEC c
  ON (a.TDACMV = c.NUMTIE AND a.CAJCMV = c.CAJA AND a.TRSCMV = c.TRANSA)
WHERE a.FECCMV >= CURRENT_DATE - ? DAY
