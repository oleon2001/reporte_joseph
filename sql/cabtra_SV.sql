select cabtra_2g.*, 
       case when numero_identificacion_cliente is not null 
             and existe_serial_impresora='Si!' and Existencia_Cajero='Existe sesion y usuario cajero!'
             and existencia_tart_y_tfdp='Si!' and existencia_trcli_y_trdoc='Si!' and diferencia_tr_vs_tart=0
             and diferencia_tr_vs_trfdp=0 and dif_renglonestr_vs_tr_art='No' and dif_montobasetr_vs_tr_art='No'
             and dif_montoimpuestotr_vs_tr_art='No' and dif_montorebajatr_vs_tr_art='No' and diagnostico_articulo_transaccion='Sin Problemas!' 
             and error_descuento='No!' and item_formadepago='No existen items -1' and estatus_formadepago='Activo!'
             and PIN_CAB_TR='OFF' and PIN_TR_FDP='OFF' 
             and duplicacion_cuerpo_de_transacciones='No Existe!' and observacion_cliente_documento='Sin Problemas!'
        then 'Transaccion perfecta! VALIDA EN LAS TR, SINO, INSERTAR O EJECUTA LOS SP'
        else 'REVISA LOS CAMPOS DE ESTA TABLA' end as MENSAJE_DE_RESOLUCION_TR_ATRAPADA,
        'SELECT * FROM transaccion WHERE id=;
SELECT * FROM transaccionarticulo WHERE id_transaccion=;
SELECT * FROM transaccionformadepago WHERE id_transaccion=;
SELECT * FROM transaccioncliente WHERE id_transaccion=;
SELECT * FROM transacciondocumento WHERE id_transaccion=;' as Consulta_para_Validar       
from             
(select t.id, t.caja, t.numero, t.tipo, 
        t.numero_fiscal, t.fecha, t.estatus_transaccion, 
        t.numero_identificacion_cliente, t.nombre, t.ficha_cajero, 
        t.total_transaccion, t.existe_serial_impresora, 
       case 
           when t.existe_sesioncajero='Si!' and t.existe_usuario_cajero='Si!' then 'Existe sesion y usuario cajero!'
           when t.existe_sesioncajero='Si!' and t.existe_usuario_cajero='No' then 'Existe sesion pero no usuario!?? Consulta la tabla usuario'
           when t.existe_sesioncajero='No' and t.existe_usuario_cajero='Si!' then 'Existe usuario! pero no sesion?? Consulta la tabla sesion' 
           else 'Consulta la tabla sesion y usuario!! No hay registro del cajero!' end as Existencia_Cajero,
       case 
           when ta.id_transaccion is null and trf.id_transaccion is null then 'No existen registros en TR_ART y TR_FDP'
           when ta.id_transaccion is null and trf.id_transaccion is not null then 'No existen registros en TR_ART'
           when ta.id_transaccion is not null and trf.id_transaccion is null then 'No existen registros en TR_FDP'
        else 'Si!' end as existencia_tart_y_tfdp,
       case 
           when trcli.id_transaccion is null and trd.id_transaccion is null then 'No existen registros en TR_CLI y TR_DOC'
           when trcli.id_transaccion is null and trd.id_transaccion is not null then 'No existen registros en TR_CLI'
           when trcli.id_transaccion is not null and trd.id_transaccion is null then 'No existen registros en TR_DOC'
           else 'Si!'end as existencia_trcli_y_trdoc,
       (t.total_transaccion-coalesce(ta.total_art,0)) as diferencia_tr_vs_tart, 
       ((t.total_transaccion + t.vuelto + t.donacion)-coalesce(trf.total_formadepago,0)) as diferencia_tr_vs_trfdp,
       case 
           when (t.renglones-coalesce(ta.renglones_tart,0))<0 and ta.Renglon_duplicado=0 then 'Sobra renglones en TR_ART'
           when (t.renglones-coalesce(ta.renglones_tart,0))<0 and ta.Renglon_duplicado=1 then 'Sobra renglones en TR_ART: Existen registros duplicados!'
           when (t.renglones-coalesce(ta.renglones_tart,0))=0 and ta.Renglon_duplicado=0 then 'No'
           when (t.renglones-coalesce(ta.renglones_tart,0))=0 and ta.Renglon_duplicado=1 then 'No, pero existen registros duplicados en TR_ART!'
           when (t.renglones-coalesce(ta.renglones_tart,0))>0 and ta.Renglon_duplicado=0 then 'Falta renglones en TR_ART'
           when (t.renglones-coalesce(ta.renglones_tart,0))>0 and ta.Renglon_duplicado=1 then 'Falta renglones en TR_ART: Existe registros duplicados en TR_ART'
       else 'desconocido' end as dif_renglonestr_vs_tr_art,
       case 
           when (t.bt-coalesce(ta.b_tart,0))<0 and ta.Variacion_b=0 then 'Sobra en tr_art'
           when (t.bt-coalesce(ta.b_tart,0))<0 and ta.Variacion_b=1 then 'Sobra en tr_art: El total_base no es igual a cantidad*Monto_base!'
           when (t.bt-coalesce(ta.b_tart,0))=0 and ta.Variacion_b=0 then 'No'
           when (t.bt-coalesce(ta.b_tart,0))=0 and ta.Variacion_b=1 then 'No, pero el total_base no es igual a cantidad*Monto_base!'
           when (t.bt-coalesce(ta.b_tart,0))>0 and ta.Variacion_b=0 then 'Falta en tr_art'
           when (t.bt-coalesce(ta.b_tart,0))>0 and ta.Variacion_b=1 then 'Falta en tr_art: El total_base no es igual a cantidad*Monto_base!'
       else 'desconocido' end as dif_montobasetr_vs_tr_art,
       case 
           when (t.it-coalesce(ta.i_tart,0))<0 then 'Sobra en tr_art'
           when (t.it-coalesce(ta.i_tart,0))=0 then 'No'
           when (t.it-coalesce(ta.i_tart,0))>0 then 'Falta en tr_art'
       else 'desconocido' end as dif_montoimpuestotr_vs_tr_art,
       case 
           when (t.rt-coalesce(ta.r_tart,0))<0 and ta.Variacion_r=0 then 'Sobra en tr_art'
           when (t.rt-coalesce(ta.r_tart,0))<0 and ta.Variacion_r=1 then 'Sobra en tr_art: El total_rebaja no es igual a cantidad*Monto_Rebaja'
           when (t.rt-coalesce(ta.r_tart,0))=0 and ta.Variacion_r=0 then 'No'
           when (t.rt-coalesce(ta.r_tart,0))=0 and ta.Variacion_r=1 then 'No, pero el total_rebaja no es igual a cantidad*Monto_Rebaja'
           when (t.rt-coalesce(ta.r_tart,0))>0 and ta.Variacion_r=0 then 'Falta en tr_art'
           when (t.rt-coalesce(ta.r_tart,0))>0 and ta.Variacion_r=1 then 'Falta en tr_art: El total_rebaja no es igual a cantidad*Monto_Rebaja'
       else 'desconocido' end as dif_montorebajatr_vs_tr_art,
       case 
           when ta.estatus_registro_articulo='Sin Problemas!' and ta.estatus_descuento_articulo='Sin Problemas!' then 'Sin Problemas!'
           when ta.estatus_registro_articulo='Sin Problemas!' 
           and ta.estatus_descuento_articulo='?' then 'articulos con descuento no registrado en la tabla tipodescuento, ejecuta el siguiente query para localizar los descuentos: select a.id_articulo, a.id_tipodescuento, b.id as registro_id_tipodescuento 
         from transaccionarticulo a left join tipodescuento b on a.id_tipodescuento=b.id where a.id_transaccion in (:id_transaccion)  and b.id is null;' 
           when ta.estatus_registro_articulo='?' 
            and ta.estatus_descuento_articulo='Sin Problemas!' then 'articulo no registrado en la tabla articulo, ejecuta el siguiente query para localizar los articulos: select a.id_articulo, b.id as registro_id_articulo 
         from transaccionarticulo a left join articulo b on a.id_articulo=b.id where a.id_transaccion in (:id_transaccion)  and b.id is null;'
       else 'articulos no estan ligados a sus tablas, peligro! puede que no exista registros en tr_art o que el articulo no se encuentra en la tabla articulo, al igual que su descuento en la tabla descuento'
       end as diagnostico_articulo_transaccion,
      ta.error_descuento,  trf.item_formadepago, trf.estatus_formadepago,
      case when ta.descuento_duplicado='No Existe!' and trf.monto_duplicado_1='No Existe!' and trcli.registro_duplicado_tr_cli='No Existe!' then 'No Existe!'
           when ta.descuento_duplicado='No Existe!' and trf.monto_duplicado_1='No Existe!' and trcli.registro_duplicado_tr_cli='Si!' then 'Registros duplicados en TRCLI'
           when ta.descuento_duplicado='No Existe!' and trf.monto_duplicado_1='Existe!' and trcli.registro_duplicado_tr_cli='No Existe!' then 'Existe monto duplicado con la misma forma de pago y con item -1 en TR_FDP'
           when ta.descuento_duplicado='No Existe!' and trf.monto_duplicado_1='Existe!' and trcli.registro_duplicado_tr_cli='Si!' then 'Existe monto duplicado con la misma forma de pago y con item -1 en TR_FDP + Registros duplicados en TR_CLI'
           when ta.descuento_duplicado='Existe!' and trf.monto_duplicado_1='No Existe!' and trcli.registro_duplicado_tr_cli='No Existe!' then 'Existe descuento duplicado en TR_ART'
           when ta.descuento_duplicado='Existe!' and trf.monto_duplicado_1='No Existe!' and trcli.registro_duplicado_tr_cli='Si!' then 'Existe descuento duplicado en TR_ART y registros duplicados en TR_CLI'
           when ta.descuento_duplicado='Existe!' and trf.monto_duplicado_1='Existe!' and trcli.registro_duplicado_tr_cli='No Existe!' then 'Existe descuento duplicado en TR_ART y monto duplicado con la misma forma de pago y con item -1 en TR_FDP'
          else 'desconocido' end as duplicacion_cuerpo_de_transacciones,
      case when trcli.existencia_vaciacliente='No' and trd.documento_inactivo='No' then 'Sin Problemas!'
           when trcli.existencia_vaciacliente='No' and trd.documento_inactivo='Si!' then 'El campo esimpreso de TR_DOC esta inactivo o el tipo de documento de TR_DOC apunta a un documento con el campo esfiscal N en la tabla tipodocumento, debe existir al menos un registros en TR_DOC con un tipo de documento que apunte a un documento fiscal'
           when trcli.existencia_vaciacliente='Si!' and trd.documento_inactivo='No' then 'La descripcion del nit en TR_CLI esta en blanco'
           when trcli.existencia_vaciacliente='Si!' and trd.documento_inactivo='Si!' then 'La descripcion del nit en TR_CLI esta en blanco y el campo esimpreso de TR_DOC esta inactivo o el tipo de documento de TR_DOC apunta a un documento con el campo esfiscal N en la tabla tipodocumento, debe existir al menos un registros en TR_DOC con un tipo de documento que apunte a un documento fiscal'
           else 'desconocido' end as observacion_cliente_documento,
      case when (t.bt + t.it)!=t.total_transaccion OR (t.vuelto + t.donacion)>=t.total_transaccion THEN 'ON! Existen problemas en la tabla transaccion los campos total_base/impuesto o vuelto/donacion no se comparan con total_transaccion' else 'OFF' end PIN_CAB_TR,     
      case when ((t.total_transaccion + t.vuelto + t.donacion)-coalesce(trf.total_formadepago,0))>0 and monto_duplicado_2>0 and trf.c_monto_duplicado_2*(t.total_transaccion + t.vuelto + t.donacion)=monto_duplicado_2 then 'ON! La diferencia tr_vs_trfdp es causado por duplicacion real en TR_FDP' else 'OFF' end PIN_TR_FDP,   
      case 
          when ta.cantidad='Si' and trd.L_extrema='No' then 'ON! Cantidad de articulos MASIVAS en TR_ART! La TR puede tener problemas en cambiar a ''A'' en ventas porque la diferencia trdmov vs trctov sera significativa, comparar con tolerancia!' 
          when ta.cantidad='No' and trd.L_extrema='Si' then 'ON! Longitud de documento en TR_DOC sobrepasa la longitud permitida, la transaccion tendra problemas para subir!'
          when ta.cantidad='Si' and trd.L_extrema='Si' then 'ON! Cantidad de articulos MASIVAS en TR_ART! La TR puede tener problemas en cambiar a ''A'' en ventas porque la diferencia trdmov vs trctov sera significativa, comparar con tolerancia! y Longitud de documento en TR_DOC sobrepasa la longitud permitida, la transaccion tendra problemas para subir!'
          else 'OFF' end as PIN_EMERGENCIA_TR
          from 
(select a.id, 
        s.id_caja as caja, 
        a.numero, 
        a.numero_fiscal, 
        a.tipo, 
        case 
          when a.estado='I' then 'Transaccion incompleta!'	
	        when a.estado='E' then 'Transaccion en espera!'
	        when a.estado='R' then 'Transaccion en espera guatefactura!'
	        else 'Transaccion finalizada' end as estatus_transaccion,
	    a.fecha, 
        c.nombre, 
	    c.numero_identificacion_cliente,
	  case when s.id is not null then 'Si!' else 'No' end as existe_sesioncajero,
	  case when b.id is not null then 'Si!' else 'No' end as existe_usuario_cajero,
	  case when d.id is not null then 'Si!' else 'No existe registro en la tabla serialimpresora!' end as existe_serial_impresora,    	  
	   b.ficha as ficha_cajero, 
       a.renglones, 
       a.vuelto,
       a.donacion,
	   a.total_base as bt,
       a.total_impuesto as it,
       a.total_rebaja as rt,
       a.total_transaccion
from transaccion a 
	left join sesion s on s.id=a.id_sesion
	left join usuario b on b.id=a.id_usuario
	left join cliente c on c.numero_identificacion_cliente=a.numero_identificacion_cliente
	left join serialimpresora d on a.id_serialimpresora=d.id
where a.id in (:id_transaccion) ) as t
left join ( 
select id_transaccion, 
       case when sum(descuentos_duplicados)>0 then 'Existe!' else 'No Existe!' end as descuento_duplicado,
       sum(renglones_tart) renglones_tart,
       case when (sum(s_existencia_trart_art)- sum(c_existencia_trart_art))=0 then 'Sin Problemas!' 
       else '?'
       end as estatus_registro_articulo,
       case when (sum(s_existencia_trartd_td)- sum(c_existencia_trartd_td))=0 then 'Sin Problemas!' 
       else '?'
       end as estatus_descuento_articulo,
       case when sum(error_descuento)=0 then 'No!' 
       else 'Rebaja sin descuento, ejecuta el siguiente query para localizar el registro: select id, id_articulo, id_transaccion, id_tipodescuento, total_rebaja
       from transaccionarticulo where id_transaccion in (:id_transaccion)  and id_tipodescuento=1 and total_rebaja>0'
       end as error_descuento,
       case when sum(cantidad)>1000 THEN 'Si'
       ELSE 'No' end as cantidad,
       case when sum(Renglon_duplicado)>0 then 1 else 0 end as Renglon_duplicado,
       case when sum(delta_b)>0 then 1 else 0 end as Variacion_b,
       sum(total_b) as b_tart,
       case when sum(delta_r)>0 then 1 else 0 end as Variacion_r,
       sum(total_r) as r_tart,
       sum(total_i) as i_tart,
       sum(total_art) as total_art
from
(select id_transaccion, id_articulo, (count(id_tipodescuento)-1) descuentos_duplicados,
       sum(renglones_tart) renglones_tart, 
       sum(existencia_trart_art) s_existencia_trart_art,
       count(existencia_trart_art) c_existencia_trart_art, 
       sum(existencia_trartd_td) s_existencia_trartd_td,
       count(existencia_trartd_td) c_existencia_trartd_td,
       sum(error_descuento) error_descuento,
       sum(cantidad) as cantidad,
       sum(Renglon_duplicado) Renglon_duplicado,
       sum(delta_b) delta_b, sum(total_b) total_b,
       sum(delta_r) delta_r, sum(total_r) total_r,
       sum(total_i) total_i, sum(total_articulo) total_art  
from 
(select  ta.id_transaccion, ta.id_articulo, ta.id_tipodescuento,
        count(ta.id_articulo) as renglones_tart,
		case when sum(ta.id_articulo-coalesce(a.id,0))=0 then 1 else 0 end as existencia_trart_art,
		case when sum(ta.id_tipodescuento-coalesce(td.id,0))=0 then 1 else 0 end as existencia_trartd_td,
		case when sum(case when ta.total_rebaja>0 and ta.id_tipodescuento=1 then 1 else 0 end)>0 then 1 else 0 end as error_descuento,
		sum(cantidad) as cantidad,
		case WHEN count(ta.total_base)>1 THEN 1 ELSE 0 END Renglon_duplicado,
		sum(abs((ta.cantidad*ta.monto_base)-ta.total_base)) as delta_b,
 		sum(ta.total_base) as total_b,
 		sum(abs(ta.cantidad*(ta.monto_unitario-ta.monto_base)-ta.total_rebaja)) as delta_r,
 		sum(ta.total_rebaja) as total_r,
		sum(total_impuesto) as total_i,
		sum(total_articulo) as total_articulo
  from 	transaccionarticulo ta 
	left join articulo a on a.id=ta.id_articulo
	left join tipodescuento td on td.id=ta.id_tipodescuento
	where ta.id_transaccion in (:id_transaccion) 
  group by ta.id_transaccion, ta.id_articulo, ta.id_tipodescuento, ta.total_base) t_art GROUP BY id_transaccion, id_articulo, id_tipodescuento) AS tart GROUP BY id_transaccion)
as ta on t.id=ta.id_transaccion
left join
(select id_transaccion,
       case when avg(item_fdp)=1 then 'No existen items -1' else '-- existen al menos un item -1, ejecuta el siguiente query: 
       select * from cr400.transaccionformadepago where id_transaccion in (:id_transaccion)  and item<0;' end as item_formadepago,
       sum(monto_moneda_local) as total_formadepago,
       case when sum(monto_duplicado_1)>0 then 'Existe!' else 'No Existe!' end as monto_duplicado_1,
       sum(monto_duplicado_2) as monto_duplicado_2,
       sum(c_monto_duplicado_2) as c_monto_duplicado_2,
       case when avg(fdp_a)=1 then 'Activo!' else '-- Forma de pago inactiva, ejecuta el siguiente query: 
       select * from cr400.transaccionformadepago where id_transaccion in (:id_transaccion)  and estaactivo=''N'';' end estatus_formadepago
       from
(select tfdp.id_transaccion,tfdp.id_formadepago,                        
       case when avg(tfdp.item)=1 then 1 else 0 end as item_fdp,
       sum(tfdp.monto_moneda_local) as monto_moneda_local,
       case when (count(tfdp.monto_moneda_local)-1)>0 and min(tfdp.item)=0 then 1 else 0 end as monto_duplicado_1,
       case when (count(tfdp.monto_moneda_local)-1)>0 and min(tfdp.item)=1 then sum(tfdp.monto_moneda_local) else 0.0 end as monto_duplicado_2,
       case when (count(tfdp.monto_moneda_local)-1)>0 and min(tfdp.item)=1 then count(tfdp.monto_moneda_local) else 0 end as c_monto_duplicado_2,
       case when avg(tfdp.fdp_a)=1 then 1 else 0 end fdp_a
from       
(select id_transaccion, id_formadepago,
       case when item>0 then 1 else 0 end as item, monto_moneda_local,
	   case when estaactivo='S' then 1 else 0 end as fdp_a
   from transaccionformadepago
   where id_transaccion in (:id_transaccion) ) as tfdp
   group by tfdp.id_transaccion, tfdp.id_formadepago, tfdp.monto_moneda_local) as cabfdp group by id_transaccion) as trf
on t.id=trf.id_transaccion
left join
(select id_transaccion, 
       case when count(id)>1 then 'Si!' else 'No Existe!' end registro_duplicado_tr_cli, 
       case when count(case when numero_identificacion_cliente=' ' then 1 end)>0 then 'Si!' else 'No' end 
       as existencia_vaciacliente
       from transaccioncliente 
       where id_transaccion in (:id_transaccion) 
       group by id_transaccion) as trcli
on t.id=trcli.id_transaccion
left join 
(select id_transaccion,
       case when (count(case when esimpreso='N' then 1 end) + avg(case WHEN esfiscal='N' then 1 else 0 end))>0 then 'Si!' else 'No'  end as documento_inactivo,
       case WHEN count(CASE WHEN length(documento)>12000 THEN 1 END)>0 THEN 'Si' 
       ELSE 'No' END AS L_extrema 
from(       
select td.id_transaccion, td.esimpreso, 
       td.documento, tpd.esfiscal
       from transacciondocumento td
       left join tipodocumento tpd on tpd.id=td.id_tipodocumento
       where id_transaccion in (:id_transaccion) ) AS tdoc group by id_transaccion) as trd
on t.id=trd.id_transaccion) as cabtra_2g;