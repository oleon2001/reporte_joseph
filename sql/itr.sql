SELECT x.ID AS ID_TRANSACCION,
        '  TIENDA: '||x.TIENDA||'   CAJA: '||x.CAJA||'   TR: '||x.TRANSACCION AS DATOS_DE_LA_TRANSACCION,
        x.CLIENTE, x.FECHA, x.CAJERO, x.TOTAL_TRANSACCION,
        CASE
            WHEN x.STACMV IS NULL
            THEN
            (CASE
                WHEN delta_t<-0.5 THEN 'La transaccion sube con '||-delta_t||' horas adelantadas! Que ocurre??'
                WHEN delta_t between -0.5 AND 0.5 THEN ' NICE! Subiendo transaccion a Legacy! '
                WHEN delta_t between 0.5 AND 0.7 THEN 'La transaccion intenta subir a Legacy pero no puede, inicia un estatus de TR atrapada! Espera unos minutos.'
                WHEN delta_t between 0.7 AND 1.0 THEN 'La transaccion tiene mas de 42 minutos que no sube. TR atrapada! Reportar a Caja Registradora'
                WHEN delta_t between 1.0 AND 6.0 THEN 'La transaccion tiene mas de '||delta_t||' hora que no sube a Menu Epa! TR atrapada! Reportar Caja Registradora'
                WHEN delta_t between 6.0 and 24.0 THEN ' La transaccion lleva mas de '||delta_t||' horas sin subir a Menu Epa!! TR atrapada! Reportar Caja Registradora'
             ELSE 'Grave!!! La transaccion lleva mas de '||delta_t||' horas sin subir a Menu Epa, wow!! Reportar Caja Registradora.' END)  
            WHEN x.STACMV=' '
              THEN
              (CASE
                  WHEN delta_dif_u < 0.4 THEN 'Subio a Menu Epa pero no a Central - Espera unos minutos mas y vuelve a ejecutar el ITR'
                  WHEN delta_dif_u between 0.4 AND 1.0 THEN 'Subio a Menu Epa pero no a Central - El proceso en legacy es lento, sospecho de posible retencion TR'
                  WHEN delta_dif_u between 1.0 AND 2.0 THEN 'Subio a Menu Epa pero no a Central - El proceso en legacy se ralentiza, el incidente persiste desde hace '||dec(delta_dif_u,7,1)||' horas... Inicia retencion de TR! Reportar a Caja Registradora!!'
               ELSE 'Subio a Menu Epa pero no a Central- PROCESO DETENIDO! HA PERSISTIDO POR '||dec(delta_dif_u,7,1)||' HORAS! NO SE REFLEJARA EN AS400! Reportar a Caja Registradora!! ' END)
            WHEN x.STACMV='A' AND delta_t<-1.0
              THEN 'Mira la TR esta en Menu Epa y completo su proceso. Pero algo ocurre, la fecha de la TR esta adelantada '||-delta_t||' horas respecto a la hora actual, este mensaje desaparecera cuando
la fecha de la transaccion sea mayor o igual a la fecha actual, por favor informa al equipo de caja esto no es normal!'
              ELSE 'Se encuentra en Menu Epa, proceso retenido?? No entiendo lo que ocurre... Reportar al equipo de caja registradora'
          END AS Analista_MOV_TR,
          CASE
              WHEN x.CAJA IS NULL OR X.CAJERO IS NULL  OR CLIENTE IS NULL
              THEN ' Activada! PELIGRO escalar a los analista de caja! CLAVES FORANEAS CON PROBLEMAS!'
              WHEN delta_t<-0.5
              THEN ' ALERTA! Transaccion tiene fecha mayor a la actual!!!'
              WHEN delta_dif>=1
              THEN ' ACTIVADO! Transaccion tiene fechas diferentes entre CR400 vs Menu Epa, se observan diferencia de '||dec(-delta_dif,7,1)||' horas.'
              WHEN (delta_dif_u+1)<0
              THEN ' ACTIVADO! Transaccion subio con fecha mayor a la actual, existen '||dec(-delta_dif_u,7,1)||' horas de diferencia, que ocurre?'
              WHEN delta_dif_u>1.0
              THEN 'OJO! La Transaccion subio muy tarde y no ha completado su recorrido, puede ser un soporte reciente o estan retenidas... Notificar a caja registradora.'
              ELSE ' '
          END AS PIN_EMERGENCIA_TR
     FROM (
   SELECT A.ID, SUBSTRING(digits(A.ID),1,3) as TIENDA, s.ID_CAJA AS CAJA,
        A.NUMERO AS TRANSACCION, trim(CLI.NOMBRE)||'--> CEDULA: '||trim(CLI.NUMERO_IDENTIFICACION_CLIENTE) AS CLIENTE,
        A.FECHA, U.FICHA AS CAJERO, A.TOTAL_TRANSACCION, v.STACMV,
        CASE
           WHEN 24*(DAYS(CURRENT_TIMESTAMP) - DAYS(A.FECHA)) + (HOUR(CURRENT_TIMESTAMP) - HOUR(A.FECHA))=0
           THEN dec(round(0.0167*(MINUTE(CURRENT_TIMESTAMP) - MINUTE(A.FECHA)),1),8,1)
           ELSE 24*(DAYS(CURRENT_TIMESTAMP) - DAYS(A.FECHA)) + (HOUR(CURRENT_TIMESTAMP) - HOUR(A.FECHA)) end as delta_t,
        abs(24*(DAYS(a.FECHA)-DAYS(v.FECCMV)) + (HOUR(a.FECHA)-substring(trim(v.HORCMV),1,2)) + 0.0167*(MINUTE(a.FECHA)-substring(trim(v.HORCMV),3,2))) AS delta_dif,
        (24*(DAYS(CURRENT_TIMESTAMP)-DAYS(V.FECCMV)) + (HOUR(CURRENT_TIMESTAMP)-substring(trim(v.HORCMV),1,2)) + 0.0167*(MINUTE(CURRENT_TIMESTAMP)-substring(trim(v.HORCMV),3,2))) AS delta_dif_u  
     FROM CR400.TRANSACCION A
     LEFT JOIN CR400.SESION S ON S.ID=A.ID_SESION
     LEFT JOIN CR400.USUARIO U ON U.ID=A.ID_USUARIO
     LEFT JOIN CR400.CLIENTE CLI ON CLI.NUMERO_IDENTIFICACION_CLIENTE=A.NUMERO_IDENTIFICACION_CLIENTE
     LEFT JOIN VENTAS.TRCMOV v ON (v.TDACMV, v.CAJCMV, v.TRSCMV)=(SUBSTRING(digits(A.ID),1,3), S.ID_CAJA, A.NUMERO)
     WHERE A.ESTADO='F'
       AND A.NUMERO_FISCAL>1
       AND date(A.FECHA) BETWEEN :FechaInicial AND :FechaFinal
       AND (COALESCE(v.STACMV,'N') <> 'A'
       OR abs(24*(DAYS(a.FECHA)-DAYS(v.FECCMV)) + 1.0*(HOUR(a.FECHA)-substring(trim(v.HORCMV),1,2)) + 0.0167*(MINUTE(a.FECHA)-substring(trim(v.HORCMV),3,2)))>=1
       OR (24*(DAYS(CURRENT_TIMESTAMP)-DAYS(V.FECCMV)) + 1.0*(HOUR(CURRENT_TIMESTAMP)-substring(trim(v.HORCMV),1,2)))<0)) AS x
UNION
SELECT CAST(s.id_tabla AS NUMERIC(22)) as id_transaccion,
       '   CAJA: '||s.id_caja||'   ----> Atrapada en la caja!' as DATOS_DE_LA_TRANSACCION,
       ' ' as Cliente,
       s.fecha AS fecha,
       -1 as Cajero,
        0 as Total_transaccion,
       ' La transaccion intenta sincronizar para llegar a la tienda pero presenta incidencias!' as Analista_MOV_TR,
       'Consejo:

-- 1. Usa la siguiente consulta de la caja para validar la transaccion:
SELECT * FROM transaccion where id='||trim(id_tabla)||';

-- 2. Si es SV, toma la fecha de (1) y usa el SFTR para solucionar el incidente, sino, reportar a caja registradora.' as PIN_EMERGENCIA_TR
 FROM CR400.sincronizacionpendientes s
 EXCEPTION JOIN CR400.TRANSACCION t ON t.id=s.id_tabla
 WHERE id_sincronizacion=50
   AND date(s.FECHA) BETWEEN :FechaInicial AND :FechaFinal
   AND (1440*(DAYS(CURRENT_TIMESTAMP) - DAYS(s.FECHA)) + 60*(HOUR(CURRENT_TIMESTAMP) - HOUR(s.FECHA)) + 1*(MINUTE(CURRENT_TIMESTAMP)-MINUTE(s.FECHA)))>25;