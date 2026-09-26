

with tr_cab as (
select x.STORE Tienda,
       x.POS Caja,
       x.TICKET Numero_ticket,
       x.TR_EPA,
       x.ORIGEN_DEVOLUCION,
       x.StellarDocID,
       x.cajero Cajero,
       x.FISCALTICKETNUMBER NUmero_autorizacion,
  --     x.SERIALFISCAL,
       x.CUSTOMERID Cliente, 
       x.fecha,
       case 
       	 when x.TIPO_TR='1' then 'VENTA'
       	 when x.TIPO_TR='5' and x.TipoNotaCredito=1 then 'DEVOLUCION'
       	 when x.TIPO_TR='5' and x.TipoNotaCredito=2 then 'ANULACION'
       	else 'Desconocido' 
       end as TIPO_TRANSACCION,
       CONCAT_WS('','"',x.TICKETAMOUNT,'"') Total_transaccion,
       CONCAT_WS('','"',x.VUELTO,'"') VUELTO,
       CONCAT_WS('','"',x.DONACION,'"') DONACION,
       CONCAT_WS('','"',z.igtf_tr,'"') TOTAL_IGTF,
       z.total_pago_tr TOTAL_PAGOS,
    --   x.odooid,
        x.Marca_Integracion,
    --   x.DocumentUID,
       CONCAT_WS('',
       (case 
        when x.ValidacionFiscal!='OK'
         THEN x.ValidacionFiscal  
        else ' ' end),
--       (case 
--        when substring(x.SERIALFISCAL,1,1)!='Z' 
--        then CONCAT_WS('','
--2. El campo SERIALFISCAL posee un valor no permitido : Tabla TICKET.SERIALFISCAL : ''',COALESCE(x.SERIALFISCAL,'''NULL'''),'''
--') else ' ' end),
       (case 
        when len(trim(x.cajero))>=5 or x.cajero=0
        then CONCAT_WS('','
3. El campo CASHIER posee un valor no permitido : Tabla TICKET.CASHIER : ''',COALESCE(x.cajero,'''NULL'''),'''
') else ' ' end),
       (case 
         when len(trim(x.CUSTOMERID))<=1
        then CONCAT_WS('','
4. El campo CUSTOMERID posee un valor no permitido : Tabla TICKET.CUSTOMERID : ''',COALESCE(x.CUSTOMERID,'''NULL'''),'''
') else ' ' end),
       (case 
        when x.TIPO_TR NOT IN ('1', '2', '3','5')
        then CONCAT_WS('','
5. El campo REGTYPE posee un valor no permitido por legacy: Tabla TICKET.REGTYPE : ''',COALESCE(x.TIPO_TR,'''NULL'''),'''
') else ' ' end),
       (case 
        when x.ITEMQTY != y.REG_DET_CONDITION_QTY
        then CONCAT_WS('','
6. Los renglones registrado en la detalle no coincide con la cabecera:
 Cabecera TICKET.ITEMQTY: ''',COALESCE(x.ITEMQTY,'''NULL'''),'''
 Detalle TICKET_DETAIL:''', COALESCE(y.REG_DET_CONDITION_QTY,'''NULL'''),'''') 
   else ' ' end),
       (case 
        when x.Documento_Relacion =' ' and x.TIPO_TR != 1
        then CONCAT_WS('','
7. El documento fiscal nota de credito no tiene transaccion de origen ligada : Documento NC ''',COALESCE(x.StellarDocID,'''NULL'''),'''
') else ' ' end),
       (case 
        when x.INDEX_Motivo=1
        then CONCAT('
8. La Nota de Credito no Posee Motivo para el tipo de TR! Valide el campo Transaccion_Motivo de la tabla TICKET!
Transaccion_Motivo: ',trim(x.Transaccion_Motivo)) else ' ' end),
       (case 
        when ABS(x.TICKETAMOUNT - (x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3 + x.TAX_1_AMT + x.TAX_2_AMT + x.TAX_3_AMT + x.NO_TAX_AMT))>=0.01
        then CONCAT_WS('','
9. Error Calculo Cabecera: Total Base + Total Impuesto != Total Transaccion:','') else ' ' end),
       (case 
        when abs(y.TOTAL_PVP - ( x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3 + x.NO_TAX_AMT - x.TOTALDISCOUNTTOT)) >0.01
        then CONCAT_WS('','
10. Error Calculo Cabecera Detalle - Rebaja Incorrecta: 
Total Bruto != Total Base + Total Rebaja : 
Total Bruto: ''',COALESCE((y.TOTAL_PVP),'''NULL'''), '''
Total Base: ''',COALESCE((x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3),'''NULL'''), '''
Total Exento:''',COALESCE((x.NO_TAX_AMT),'''NULL'''),'''   
Total Rebaja: ''',COALESCE((-x.TOTALDISCOUNTTOT ),'''NULL'''), '''
Diferencia -->  ''',
        COALESCE(CONVERT( decimal(13,4),(y.TOTAL_PVP - (x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3 + x.NO_TAX_AMT - x.TOTALDISCOUNTTOT))),'''NULL'''),'''') 
   else ' ' end),
       (case 
        when error_descart!=0
        then '
11. Error Descuento Detalle - Existen articulos con Rebajas pero sin codigo descuento! Validar IndiceTipoDcto de TICKET.DETAIL.'
   else ' ' end),
       (case 
        when abs(y.TOTAL_REBAJA - x.TOTALDISCOUNTTOT) >0.01
        then CONCAT_WS('','
12. Error Calculo Cabecera Detalle - Rebaja Incorrecta: 
Total Rebaja Cabecera != Total Rebaja Detalle :','') 
   else ' ' end),
       (case 
        when (y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + TOTAL_IMPUESTO_3) - (x.TAX_1_AMT + x.TAX_2_AMT + x.TAX_3_AMT) >= 0.004
        then CONCAT_WS('','
13. Error Calculo Cabecera Detalle - Impuesto Incorrecto: Total Impuesto Cabecera != Total Impuesto Detalle :
Total Impuesto Cabecera: ''',COALESCE((x.TAX_1_AMT + x.TAX_2_AMT + x.TAX_3_AMT),'''NULL'''), ''' 
Total Impuesto Detalle: ''',COALESCE((y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + TOTAL_IMPUESTO_3),'''NULL'''), '''
Diferencia -->  ''',
        COALESCE(CONVERT( decimal(13,4),((y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + TOTAL_IMPUESTO_3) - (x.TAX_1_AMT + x.TAX_2_AMT + x.TAX_3_AMT))),'''NULL'''),'''') 
   else ' ' end),
       (case 
        when (y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + TOTAL_BASE_3) - (x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3) >= 0.004
        then CONCAT_WS('','
14. Error Calculo Cabecera Detalle - Base Incorrecto: Total Base Cabecera != Total Base Detalle : 
Diferencia -->  ''',
        COALESCE(CONVERT( decimal(13,4),((y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + TOTAL_BASE_3) - (x.TOTBAS1 + x.TOTBAS2 + x.TOTBAS3))),'''NULL'''),'''') 
   else ' ' end),
       (case 
        when ABS(y.TOTAL_ARTICULO - x.TICKETAMOUNT) > =0.05
        then CONCAT_WS('','
15. Error Calculo Cabecera Detalle - Total TR Incorrecto: Total TR Detalle != Total TR Cabecera :','') 
   else ' ' end),
       (case 
        when ABS(y.TOTAL_PVP -(y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT - y.TOTAL_REBAJA)) > 0.01
        then CONCAT_WS('','
16. Error Calculo Detalle - Base Incorrecta: Total Base Detalle != Total Bruto Detalle - Total Rebaja Detalle:',' 
Total Base Detalle: ''',COALESCE((y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT),'''NULL'''), ''' 
Total Bruto Detalle: ''', COALESCE((y.TOTAL_PVP),'''NULL'''),'''
Total Rebaja Detalle: ''', COALESCE((y.TOTAL_REBAJA),'''NULL'''),'''
Diferencia -->  ''',
        COALESCE(CONVERT( decimal(13,4),(y.TOTAL_PVP  - (y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT - y.TOTAL_REBAJA))),'''NULL'''),'''') 
   else ' ' end),
       (case 
        when ABS((y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + y.TOTAL_IMPUESTO_3) - (TOTAL_IMPUESTO_CAL_1 + TOTAL_IMPUESTO_CAL_2 + TOTAL_IMPUESTO_CAL_3))>=0.01
        then '
17. Error Calculo Detalle Impuesto- Existe articulos con Total impuesto incorrecto cuando se compara con la tasa de iva grabada' 
   else ' ' end),
       (case 
        when abs(y.TOTAL_ARTICULO - (y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT) - (y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + y.TOTAL_IMPUESTO_3))>=0.001
        then CONCAT_WS('','
18. Error Calculo Detalle - Total Articulo Incorrecto: Total Articulo != Total Base Articulo + Total Impuesto Articulo :','
Total Base Detalle: ''',COALESCE((y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT),'''NULL'''), ''' 
Total Impuesto Detalle: ''', COALESCE(((y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + y.TOTAL_IMPUESTO_3)),'''NULL'''),''',
Total Articulo Detalle: ''',COALESCE(y.TOTAL_ARTICULO,'''NULL'''), ''',
Total Articulo Calculado: ''',COALESCE((y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT) + (y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + y.TOTAL_IMPUESTO_3),'''NULL'''), ''',
Diferencia: ''',COALESCE(ABS(y.TOTAL_ARTICULO - (y.TOTAL_BASE_1 + y.TOTAL_BASE_2 + y.TOTAL_BASE_3 + y.NO_TAX_AMT) - (y.TOTAL_IMPUESTO_1 + y.TOTAL_IMPUESTO_2 + y.TOTAL_IMPUESTO_3)),'''NULL'''), ''',
')
   else ' ' end),
 /*      (case 
        when z.reg_porc_igtf !=0 and z.tasa_cambio_registradas!=0 
        and abs(0.03*(case when (x.TICKETAMOUNT - z.total_bs)>= z.total_divisas then z.total_divisas else (x.TICKETAMOUNT - z.total_bs) end) - z.igtf_tr)>=0.01
        then CONCAT_WS('','
19. Error Calculo Igft FDP - Igtf TR Incorrecto: IGTF TR != IGTF FDP :','
Total Transaccion: ''',COALESCE(CONVERT( decimal(13,4),(x.TICKETAMOUNT)),'''NULL'''), '''
Base Imponible Guardado: ''',COALESCE(CONVERT( decimal(13,4),(z.b_imponible)),'''NULL'''),''' 
Base imponible Calculado: ''', COALESCE(CONVERT( decimal(13,4),((case when (x.TICKETAMOUNT - z.total_bs)>= z.total_divisas then z.total_divisas else (x.TICKETAMOUNT - z.total_bs) end))),'''NULL'''),'''
Diferencia Imponible: ''',COALESCE(CONVERT( decimal(13,4),(z.b_imponible - (case when (x.TICKETAMOUNT - z.total_bs)>= z.total_divisas then z.total_divisas else (x.TICKETAMOUNT - z.total_bs) end))),'''NULL'''),''' 
IGTF FDP Guardado -->  ''',COALESCE(CONVERT( decimal(13,4),(z.igtf_tr)),'''NULL'''),'''
IGTF TR Calculado -->  ''',COALESCE(CONVERT( decimal(13,4),(0.03*(case when (x.TICKETAMOUNT - z.total_bs)>= z.total_divisas then z.total_divisas else (x.TICKETAMOUNT - z.total_bs) end))),'''NULL''')
,'''') 
   else ' ' end),
       (case 
        when z.fdp_divisas!=0 and z.igtf_tr=0
        then '
20. Existen FDP que generan IGTF en la transaccion pero en MEDIA_PAY el total IGTF = 0'
   else ' ' end),*/
--       (case 
--        when z.fdp_divisas!=0 and z.tasa_cambio_registradas=0
--        then '
--21. Existen FDP que generan IGTF en la transaccion pero en MEDIA_PAY no se registra la tasa de cambio'
--   else ' ' end),
       (case 
        when abs(2 * x.TICKETAMOUNT - (y.TOTAL_ARTICULO + (z.total_pago_tr - z.igtf_tr - x.vuelto - x.donacion)))>=0.01
        then CONCAT_WS('','
22. Error Calculo TR - Totales transaccion Incorrecto:','
Total TR: ''',COALESCE((x.TICKETAMOUNT),'''NULL'''), '''
Total Detalle TR: ''', COALESCE((y.TOTAL_ARTICULO),'''NULL'''),'''
Total TR FDP: ''',COALESCE((z.total_pago_tr),'''NULL'''),'''
Vuelto TR: ''',CONVERT( decimal(13,4),((x.VUELTO))),'''
Donacion TR:''',CONVERT( decimal(13,4),((x.donacion))),'''
Formula - Diferencia TR: 2 * Total TR - (Total Detalle TR + (Total TR FDP - (Vuelto TR + Donacion TR))); 
Diferencia: ''',COALESCE(CONVERT( decimal(13,4),(2 * x.TICKETAMOUNT - (y.TOTAL_ARTICULO + (z.total_pago_tr - z.igtf_tr - x.vuelto - x.donacion)))),'''NULL'''),'''')else '
' end),
     /*  (case 
        when x.STORE !=:tda
        then concat_Ws('','
23. Tienda o Sucursal Incorrecta! La TR se guarda con un tienda != tienda origen: ',:tda,'!.') 
   else ' ' end),*/
       (case 
        when y.DIFDET_REBAJA !=0
        then '
24. Error de calculo por rebaja! Existen articulos que al aplicar el porcentaje de la rebaja no se obtiene el total articulo calculado!' 
   else ' ' end),
/*       (case 
        when x.VUELTO!=0 and z.reg_vuelto_asociado=0
        then '
25. La forma de pago del vuelto no coincide con las formas de pago de la transaccion!' 
   else ' ' end),
       (case 
        when x.DONACION!=0 and z.reg_donacion_asociado=0
        then '
26. La forma de pago de la donacion no coincide con las formas de pago de la transaccion!' 
   else ' ' end),*/
       (case 
        when z.fdp_desc!=0
        then '
25. La forma de pago de la transaccion esta descrita por texto no por codigo fdp!' 
   else ' ' end),/*,
       (case 
        when x.c_CODCLIENTE IS NULL
        then '
25. Error Cliente! El cliente de la transaccion no se encuentra en MA_CLIENTES!' 
   else ' ' end)*/
       (case 
        when yf.reg_frequency !=0
        then concat_ws('','
26. Articulos con descuentos repetidos en el detalle! VALIDAR TICKET.DETAIL.
Codigos Articulos: ',F1_CODIGO,(case when F1_CODIGO!=F2_CODIGO then CONCAT(' y ', F2_CODIGO ) else ' .' end)) 
   else ' ' end),
       (case 
        when y.REG_DET = 0
        then '
27. Grave!! No hay registros en TICKET.DETAIL!!'
   else ' ' end),
   (case 
        when error_redescart!=0
        then '
28. Error Descuento Detalle - Existen articulos que tienen codigo o porcentaje de descuento pero no guardaron rebaja ! Validar TOTDISCOUNT en TICKET.DETAIL.'
   else ' ' end),
   (case 
        when error_redescart_emp!=0
        then '
29. Error Descuento Detalle - Existen articulos con DESCUENTO EMPLEADO que no guardaron rebaja! Validar DISCOUNT_RATE  y TOTDISCOUNT en TICKET.DETAIL.'
   else ' ' end),
   (case 
        when y.leng_codart!=0
        then '
30. Existe codigos articulos que no tienen los 7 digitos que le corresponden! Validar el campo PluDefaultCode de TICKET_DETAIL!'
   else ' ' end),
   (case 
        when x.donacion!=0 and x.REG_DET_DON=0
        then '
31. Error Donacion : Existe cabecera pero no detalle! MA_DONACIONES NO COINCIDEN CON MA_DONACIONES_DETPAG!'
   else ' ' end),
   (case 
        when x.TIPO_TR='5' and x.REG_EXIST_VNC=0
        then '
32. Error Relacion Venta/Nota de Credito : No existe registro de Documento_Relacion(VENTA) en la tabla TICKET! ' 
   else ' ' end),
   (case 
        when COALESCE(total_pago_tr,'0')=0
        then '36. No existe registros en VENTASSTORE.MEDIA_PAY??'
   else ' ' end)
) Observaciones,
case when x.CUSTOMERID!='CF' and (select count(1) from VENTASSTORE.dbo.MA_CLIENTES mc where mc.c_CODCLIENTE = x.CUSTOMERID)=0
     and  (
     (select count(1) from VAD10.dbo.MA_CLIENTES mc where mc.c_CODCLIENTE =x.CUSTOMERID COLLATE Modern_Spanish_CI_AS)=0 or 
     (select count(1) from VAD10.dbo.MA_CLIENTES mc where CONVERT(date, add_date)!='1900-01-01' and mc.c_CODCLIENTE =x.CUSTOMERID COLLATE Modern_Spanish_CI_AS)!=0)
    then 'Existe Cliente Transacion pero no se guardo en VENTASSTORE.MA_CLIENTES, cliente no migrado a ERP EPA'
    else '' end Observacion_cliente,
--z.cant_pagos,
concat_ws('',' 
select * from VENTASSTORE.dbo.TICKET t where t.StellarDocID =''',x.StellarDocID,''';
select * from VENTASSTORE.dbo.TICKET_DETAIL td where td.StellarDocID =''',x.StellarDocID,''';
select * from VENTASSTORE.dbo.MEDIA_PAY mp where mp.StellarDocID =''',x.StellarDocID,''';
select * from VENTASSTORE.dbo.MEDIA_CHANGE mc where mc.StellarDocID =''',x.StellarDocID,''';
select mdd.* FROM VENTASSTORE.dbo.MA_DONACIONES md inner join VENTASSTORE.dbo.MA_DONACIONES_DETPAG mdd ON 
mdd.c_Documento = md.c_Documento and mdd.c_Caja = md.c_Caja and mdd.c_Localidad = md.c_Sucursal  where RIGHT(md.c_Numero_Rel ,3) =''',x.TICKET,''' and cast(md.c_Caja as int) =',cast(x.POS as int),' and cast(md.c_Sucursal as int) =',cast(x.STORE as int),';') consulta_para_Validar
  from 
(select t.STORE, 
       t.POS, 
       t.SLSEQ, 
       t.TICKET, 
       SUBSTRING(t.DocumentUID,5,6) TR_EPA,
       t.CASHIER cajero,
       CONVERT(date, t.DDATE) fecha,
       t.ITEMQTY ITEM_VENDIDOS,
       t.SERIALFISCAL,
       t.FISCALTICKETNUMBER,
       t.ZREPORTNUMBER,
       t.CUSTOMERID,
       --mc2.c_CODCLIENTE,
       t.REGTYPE TIPO_TR,
       t.TipoNotaCredito,
       t.Transaccion_Motivo,
       (case when t.REGTYPE=1 then 1 else -1 end) cfe_tr,
       t.ITEMQTY,
       t.TICKETAMOUNT,
       TOTALPRICETOT,
       t.TOTALDISCOUNTTOT,
       t.TOTBAS1, 
       t.TOTBAS2,
       t.TOTBAS3,
       t.TOTALTAXTOT,
       t.TAX_1_AMT,
       t.TAX_2_AMT, 
       t.TAX_3_AMT,
       t.TAX_1_RATE,
       t.TAX_2_RATE,
       t.TAX_3_RATE,
       t.NO_TAX_AMT,
       t.RATE_DISCOUNT,
       t.StellarDocID,
       t.Documento_Relacion,
       (select count(1) from VENTASSTORE.dbo.TICKET t2 where t2.StellarDocID=t.Documento_Relacion) REG_EXIST_VNC,      
       0 BasIGTF, 
       0 TotIGTF,
       0 n_Base_IGTF, 
       0 n_Imp_IGTF,
       t.DocumentUID,
       t.OdooID,
       case 
	       when t.OdooID =0 then 'Pendiente'  
	       when t.OdooID =1 then 'Enviada' 
	       when t.OdooID =2 then 'Incidente Factura Electrónica ' 
	       when t.OdooID =3 then 'No paso validaciones del extractor' 
	       when t.OdooID =4 then 'No paso validaciones del procesador ' 
	       else '?' end as Marca_Integracion, 
       /*COALESCE((SELECT sum(n_Monto) 
         from VENTASSTORE.dbo.MA_DETALLEPAGO_VUELTO mdv 
         where RIGHT(mdv.c_Factura,3) =t.ticket 
           and cast(mdv.c_Caja as int) = cast(t.POS as int)
           and cast(mdv.c_Localidad  as int) = cast(t.store as int)
           and CONVERT(date, mdv.d_Fecha)=CONVERT(date, t.DDATE)),0) VUELTO,*/
       COALESCE((SELECT sum(n_Monto) 
         from VENTASSTORE.dbo.MEDIA_CHANGE mc  
         where mc.StellarDocID=t.StellarDocID),0) VUELTO, 
         COALESCE((select sum(md.n_Total) AS AMOUNT
  from VENTASSTORE.dbo.TICKET a 
  inner join VENTASSTORE.dbo.MA_DONACIONES md on (md.c_Numero_Rel) = (RIGHT(a.StellarDocID,8)) AND a.STORE = md.c_Sucursal
  inner join VENTASSTORE.dbo.MA_DONACIONES_DETPAG mdd ON (md.c_Documento=mdd.c_Documento) AND md.c_Caja = mdd.c_Caja AND md.c_Sucursal = mdd.c_Localidad
  where a.StellarDocID IN (t.StellarDocID)
   and (case when (a.REGTYPE='1' and md.c_Concepto='DON') or (a.REGTYPE='5' and md.c_Concepto='DEV') then 1 else 0 end)=1),0) DONACION,
       (select count(1)
  from VENTASSTORE.dbo.TICKET a
  inner join VENTASSTORE.dbo.MA_DONACIONES md on (md.c_Numero_Rel) = (RIGHT(a.StellarDocID,8)) AND a.STORE = md.c_Sucursal
  inner join VENTASSTORE.dbo.MA_DONACIONES_DETPAG mdd ON (md.c_Documento=mdd.c_Documento) AND md.c_Caja = mdd.c_Caja AND md.c_Sucursal = mdd.c_Localidad
  where a.StellarDocID IN (t.StellarDocID)
   and (case when (a.REGTYPE='1' and md.c_Concepto='DON') or (a.REGTYPE='5' and md.c_Concepto='DEV') then 1 else 0 end)=1) REG_DET_DON,
       (case when trim(t.Transaccion_Motivo) not in (
'2_MAL ASESORAMIENTO',
'3_DECISION DEL CLIENTE',
'6_VENC CLIENTE RETIRA',
'7_CAMBIO COND DESPACHO',
'8_VENTA SIN EXISTENCIA',
'9_CAMBIO RAZON SOCIAL',
'1_AVERIADO',
'4_AVERIADO POR IGUAL',
'5_IGUAL POR IGUAL') and t.TipoNotaCredito=1 and t.REGTYPE='5'  
then 1 
when trim(t.Transaccion_Motivo) not in (
'0_Anulacion Cliente deja mercancia',
'0_Anulacion Error en el procesamiento',
'0_Anulacion Prueba de funcionamiento',
'0_Anulacion Cambio condiciones del documento') and t.TipoNotaCredito=2 and t.REGTYPE='5'  
then 1 
else 0 end) INDEX_Motivo, 
case 
when t.REGTYPE = '5' 
 and t.TipoNotaCredito =1
 and len(t.Documento_Relacion)>13
 then 'LEGADO'
 when t.REGTYPE = '1'
 then ' '
 else 'STELLAR' END AS ORIGEN_DEVOLUCION,
 CASE 
    WHEN COALESCE(trim(t.FiscalSeries),'') = '' 
             AND COALESCE(CONVERT(date,FiscalIssueDate),'1970-01-01')='1970-01-01'
             AND COALESCE(trim(t.FiscalPrePrinted),'') = ''
             AND COALESCE(TRIM(t.FiscalReference),'')=''
             AND COALESCE(trim(t.FiscalAccessNumber),'') = ''  
             AND COALESCE(trim(t.FISCALTICKETNUMBER),'') = '' 
            THEN 'Error 1.0: Todos los campos fiscales están en blanco.'
        WHEN COALESCE(trim(t.FiscalSeries),'') = '' 
             AND COALESCE(CONVERT(date,FiscalIssueDate),'1970-01-01')='1970-01-01'
             AND COALESCE(trim(t.FiscalPrePrinted),'') = ''
             AND COALESCE(trim(t.FiscalAccessNumber),'') = '' 
             THEN 'Error 1.1: Ticket fiscal en contingencia sin número de acceso.'
        WHEN COALESCE(trim(t.FiscalSeries),'') = '' 
             AND COALESCE(CONVERT(date,FiscalIssueDate),'1970-01-01')='1970-01-01'
             AND COALESCE(trim(t.FiscalPrePrinted),'') = ''
             AND COALESCE(trim(t.FiscalAccessNumber),'') != '' 
             AND COALESCE(trim(t.FISCALTICKETNUMBER),'') != ''
             THEN 'Error 1.2: Ticket fiscal en contingencia cumple con número de acceso pero tiene numero de autorizacion.'
        WHEN COALESCE(trim(t.FiscalSeries),'') = '' 
             AND COALESCE(CONVERT(date,FiscalIssueDate),'1970-01-01')='1970-01-01'
             AND COALESCE(trim(t.FiscalPrePrinted),'') = ''
             AND COALESCE(trim(t.FiscalReference),'') = '' 
             THEN 'Error 1.3: Ticket fiscal en contingencia sin numero de referencia.'   
        WHEN COALESCE(trim(t.FiscalAccessNumber),'') = ''
             AND (
             COALESCE(trim(t.FiscalSeries),'') = '' 
             OR COALESCE(CONVERT(date,FiscalIssueDate),'1970-01-01')='1970-01-01'
             OR COALESCE(trim(t.FiscalPrePrinted),'') = ''
             ) 
             THEN 'Error 1.4: Ticket fiscal con indicadores de contigencia pero su FiscalAccessNumber se encuentra en blanco'     
        ELSE 'OK'
    END AS ValidacionFiscal
  from VENTASSTORE.dbo.TICKET t 
 where 
 CONVERT(date, t.DDATE) BETWEEN :Fi and :Ff
--   and SUBSTRING(t.TTIME,1,2)=:hora
--   and t.odooid=0
  and t.odooid<>1
--  and t.STORE = :tda
/* 
 and t.stellardocid in (
 '03VEN52013928'
)
*/
  ) x
 left join 
(select d.STORE, d.POS, d.SLSEQ , d.TICKET, 
       d.CASHIER cajero , d.StellarDocID, CONVERT(date, d.DDATE) FECHA,
       count(1) REG_DET,
       sum(case when cast(d.QTY as dec(13,4))!=0 then 1 else 0 end) REG_DET_CONDITION_QTY,
       sum((case when d.TYPMOV='05' and c.REGTYPE in ('1','5') then -1 else 1 end) * (QTY  * PRICE)) TOTAL_PVP, 
       SUM(d.TOTBAS1) TOTAL_BASE_1, 
       SUM(d.TOTBAS2) TOTAL_BASE_2, 
       SUM(d.TOTBAS3) TOTAL_BASE_3,
       SUM(d.TAX1) TOTAL_IMPUESTO_1, 
       SUM(d.TAX2) TOTAL_IMPUESTO_2,
       SUM(d.TAX3) TOTAL_IMPUESTO_3,
       SUM(d.TOTBAS1 * d.TAX_1_RATE  * 0.01) TOTAL_IMPUESTO_CAL_1,
       SUM(d.TOTBAS2 * d.TAX_2_RATE  * 0.01) TOTAL_IMPUESTO_CAL_2,
       SUM(d.TOTBAS3 * d.TAX_3_RATE  * 0.01) TOTAL_IMPUESTO_CAL_3,
       SUM(d.NO_TAX_AMT) NO_TAX_AMT,
       sum(d.TOTDISCOUNT) TOTAL_REBAJA,
       sum(case when abs(abs(d.TOTBAS1 + d.TOTBAS2 + d.TOTBAS3 + d.NO_TAX_AMT)  - abs((1-0.01*d.DISCOUNT_RATE) * d.QTY * d.PRICE))>=0.01 then 1 else 0 end) DIFDET_REBAJA,
       sum(case when (d.TOTDISCOUNT!= 0 OR d.DISCOUNT_RATE!=0) AND d.IndiceTipoDcto='0' then 1 else 0 end) error_descart,
       sum(case when (d.TOTDISCOUNT= 0 OR d.DISCOUNT_RATE=0) AND d.IndiceTipoDcto!='0' then 1 else 0 end) error_redescart,
       sum(case when (d.TOTDISCOUNT= 0 OR d.DISCOUNT_RATE=0) AND d.IndiceTipoDcto='4' then 1 else 0 end) error_redescart_emp,
       sum(case when len(d.PluDefaultCode)!=7 then 1 else 0 end) leng_codart,
       count(case when d.TOTDISCOUNT=0 then 0 else 1 end) REG_REBAJA,
       count(case when d.DISCOUNT_RATE =0 then 0 else 1 end) REG_INDICA_REBAJA,
       sum(d.TOTPRICE) TOTAL_ARTICULO
from VENTASSTORE.dbo.TICKET_DETAIL d
INNER JOIN VENTASSTORE.dbo.TICKET c on c.StellarDocID = d.StellarDocID 
group by d.STORE, d.POS, d.SLSEQ , d.TICKET, d.CASHIER, d.StellarDocID, CONVERT(date, d.DDATE)) y 
on y.STORE = x.STORE and y.POS = x.POS and y.SLSEQ =x.SLSEQ and y.TICKET = x.TICKET and  y.cajero = x.cajero and y.StellarDocID= x.StellarDocID and y.FECHA = x.FECHA
left join 
(select STORE, POS, SLSEQ , TICKET, CASHIER, FECHA, StellarDocID , sum(reg_frequency) reg_frequency, min(PluDefaultCode) F1_CODIGO, max(PluDefaultCode) F2_CODIGO
  from 
(select d.STORE, d.POS, d.SLSEQ , d.TICKET, d.CASHIER, d.StellarDocID, d.PluDefaultCode, d.IndiceTipoDcto, COUNT(1) reg_frequency,CONVERT(date, d.DDATE) fecha
from VENTASSTORE.dbo.TICKET_DETAIL d
INNER JOIN VENTASSTORE.dbo.TICKET c on c.StellarDocID = d.StellarDocID 
group by d.STORE, d.POS, d.SLSEQ , d.TICKET, d.CASHIER, d.StellarDocID, d.PluDefaultCode, d.IndiceTipoDcto,  CONVERT(date, d.DDATE)
HAVING count(1)>1) x
group by STORE, POS, SLSEQ , TICKET, CASHIER, StellarDocID, FECHA) yf
on yf.STORE = x.STORE and yf.POS = x.POS and yf.SLSEQ =x.SLSEQ and yf.TICKET = x.TICKET and  yf.CASHIER = x.cajero and yf.FECHA = x.FECHA and yf.StellarDocID=x.StellarDocID
left join 
(select STORE, POS, SLSEQ , TICKET, CASHIER cajero , StellarDocID, CONVERT(date, DDATE) FECHA,
       sum(case when mp.MEDIAGROUP in ('17','66','67','70')then MEDIAAMOUNT else 0 end) total_divisas,
       sum(case when MediaExRate=1 then MEDIAAMOUNT else 0 end) total_bs,
       sum(MEDIAAMOUNT) total_pago_tr,
       0 igtf_tr,
       0 b_imponible,
       0fdp_divisas,
       sum(case when MediaExRate > 1 then 1 else 0 end) tasa_cambio_registradas,
       0 reg_porc_igtf,
       count(1) cant_pagos,
       count(case when isnumeric(mp.MEDIACOD)=0 then 1 end) fdp_desc
from VENTASSTORE.dbo.MEDIA_PAY mp 
group by STORE, POS, SLSEQ , TICKET, CASHIER, StellarDocID, CONVERT(date, DDATE)) z
on z.STORE = x.STORE and z.POS = x.POS and z.SLSEQ =x.SLSEQ and z.TICKET = x.TICKET and  z.cajero = x.cajero and z.StellarDocID= x.StellarDocID and z.FECHA = x.FECHA)
select * from tr_cab 
--where len(trim(Observaciones))!=1
ORDER BY fecha, tienda, caja, TR_EPA;