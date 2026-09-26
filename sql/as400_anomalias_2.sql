-- Anomalía 2 (GT, AS400 Central): NO LLEGÓ A OPVTSC (documento / datos fiscales).
-- Parámetro: ? = días hacia atrás (por defecto 5).
SELECT a.TDACMV AS Tienda, a.CAJCMV AS Caja, a.TRSCMV AS TR_EPA
FROM ventas.trcmov a
EXCEPTION JOIN ventas.opevtsc c
  ON (a.TDACMV = c.TIENOTSC AND a.CAJCMV = c.CAJAOTSC AND a.TRSCMV = c.TRANOTSC)
WHERE a.FECCMV >= CURRENT_DATE - ? DAY
