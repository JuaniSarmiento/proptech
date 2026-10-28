from pathlib import Path
import subprocess, datetime, difflib, sys
root=Path.cwd()
out=Path('/tmp/2d-arreglos-v2-evidencia')
unidades='web/src/app/edificios/[id]/unidades/Pantalla.tsx'
permisos='src/app/edificios/[id]/unidades/permisos.test.tsx'
consumer='src/app/edificios/[id]/unidades/page.test.tsx'
page='web/src/app/invitacion/[sobre]/page.tsx'
pantalla='web/src/app/invitacion/Pantalla.tsx'
cases=[
 ('M1-editar',unidades,'{puedeConfigurar || puedeInvitar ? (','{true ? (',[permisos]),
 ('M2-guardar',unidades,'{puedeConfigurar ? (\n          <Formulario','{true ? (\n          <Formulario',[permisos]),
 ('M3-configuracion','web/src/app/edificios/[id]/configuracion/Pantalla.tsx','const botonCambiar = puedeCrearVersion ? (','const botonCambiar = true ? (',[permisos]),
 ('M4-saldos','web/src/app/edificios/[id]/saldos-previos/Pantalla.tsx','{puedeConfirmar ? (','{true ? (',[permisos]),
 ('M5-vecinos-consumidor',unidades,'unidadEnEdicion && vecinosPorUnidad && puedeInvitar','unidadEnEdicion && vecinosPorUnidad',[permisos,consumer]),
 ('M9-proveedor-anticipado',pantalla,'cerrandoSesion ? (','true ? (',['src/app/invitacion/Pantalla.test.tsx','-t','abrir o rechazar']),
 ('M6-cerrar-sesion',pantalla,'void clerk.signOut({ redirectUrl: destino });','void destino;',['src/app/invitacion/Pantalla.test.tsx']),
 ('M7-volver-ingreso',page,'volverAInvitacion={`${regreso}${ticket','volverAInvitacion={`${"/ingresar"}${ticket',['src/app/invitacion/[sobre]/page.test.tsx']),
 ('M8-perder-ticket',page,'volverAInvitacion={`${regreso}${ticket ?','volverAInvitacion={`${regreso}${false ?',['src/app/invitacion/[sobre]/page.test.tsx']),
]
for name, file, old, new, tests in cases:
 if len(sys.argv)>1 and name!=sys.argv[1]:continue
 p=root/file; original=p.read_text(); assert old in original, (name,old)
 backup=out/(name+'.backup');backup.write_text(original)
 mutant=original.replace(old,new,1)
 cmd=['corepack','pnpm@12.10.1','vitest','run',*tests]
 started=datetime.datetime.now().astimezone().isoformat()
 try:
  p.write_text(mutant)
  result=subprocess.run(cmd,cwd=root/'web',text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  diff=''.join(difflib.unified_diff(original.splitlines(True),mutant.splitlines(True),fromfile=file,tofile=file+' (mutante)'))
  log=f'TIME {started}\nBACKUP {backup}\nCOMMAND cd web && '+ ' '.join(cmd)+'\n'+diff+'\n'+result.stdout
  (out/(name+'.log')).write_text(log)
  print(name,'exit',result.returncode,flush=True)
  print('\n'.join(l for l in result.stdout.splitlines() if 'Tests ' in l or 'AssertionError:' in l or '❯ src/' in l),flush=True)
  if result.returncode==0:raise RuntimeError('SURVIVING MUTANT '+name)
  if 'AssertionError' not in result.stdout:raise RuntimeError('NOT ASSERTION '+name)
 finally:p.write_text(original)
