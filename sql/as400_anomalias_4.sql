-- Anomalía 4 (GT, AS400 Central): TRANSACCIONES CON ESTATUS EN BLANCO.
-- Parámetro: ? = días hacia atrás (por defecto 3).
SELECT a.TDACMV AS Tienda, a.CAJCMV AS Caja, a.TRSCMV AS TR_EPA
FROM ventas.trcmov a, ventas.trdmov b
WHERE (a.TDACMV, a.CAJCMV, a.TRSCMV) = (b.TDADMV, b.CAJDMV, b.TRSDMV)
  AND a.FECCMV >= CURRENT_DATE - ? DAY
  AND (a.STACMV <> 'A' OR b.STADMV <> 'A')
GROUP BY a.TDACMV, a.CAJCMV, a.TRSCMV
ORDER BY a.TDACMV
