-- Pendientes por imprimir (Stellar de tienda).
-- Ejecutar en el servidor Stellar de cada tienda (VE y GT).
SELECT
    c_Sucursal             AS Tienda,
    c_Caja                 AS Caja,
    c_Numero               AS TR_EPA,
    c_MotivoContingencia   AS Motivo
FROM vad20.dbo.MA_PAGOS mp
WHERE bs_Impresa <> 1
