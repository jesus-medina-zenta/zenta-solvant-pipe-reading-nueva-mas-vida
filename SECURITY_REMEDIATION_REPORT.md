# Reporte de remediación de dependencias

**Fecha:** 2026-09-02
**Servicios afectados:** zenta-solvant-pipe-reading-nueva-mas-vida (Cloud Run Job `zenta-solvant-pipe-reading`)

## Cambios aplicados

| CVE | Paquete | Versión anterior → nueva | Tipo de cambio | Acción tomada | Verificación | Estado |
|---|---|---|---|---|---|---|
| CVE-2026-28684 | python-dotenv | 1.0.0 → >=1.2.2 | minor | bump de pin en requirements.txt | pip-audit limpio, `pip check` OK, import de `src.pipeline` OK | ✅ Resuelto |
| CVE-2023-48795 (Terrapin attack) | paramiko | 3.3.1 → >=3.4.0 | minor | bump de pin | pip-audit limpio, import OK | ✅ Resuelto |
| CVE-2026-44405 | paramiko | (sin fix disponible en 3.3.1) → >=3.4.0 | minor | bump de pin (misma línea que arriba) | pip-audit limpio | ✅ Resuelto |
| CVE-2026-25645, CVE-2024-47081, CVE-2024-35195 | requests | 2.31.0 → >=2.33.0 | minor | bump de pin | pip-audit limpio, import OK | ✅ Resuelto |
| CVE-2024-52338 (deserialización insegura IPC/Feather, no estaba en el escaneo original del usuario, lo encontró pip-audit) | pyarrow | 14.0.2 → >=17.0.0 | major (14→17) | bump de pin; API de `pyarrow` usada en el proyecto (solo vía `openpyxl`/`pandas` como dependencia transitiva, no se invoca directamente) sin cambios de firma relevantes | pip-audit limpio, `pip check` OK, import OK | ✅ Resuelto |
| CVE-2026-8643, CVE-2026-6357, CVE-2026-3219, CVE-2026-13346, CVE-2025-8869 | pip | (toolchain, no en requirements.txt) | patch (toolchain) | `Dockerfile`: `pip install --upgrade pip` → `pip install --upgrade pip setuptools wheel` | pendiente de confirmar en el próximo build de imagen (no verificable con pip-audit sobre requirements.txt) | ⚠️ Pendiente de build |
| CVE-2026-24049 | wheel | (toolchain) | patch (toolchain) | mismo cambio de Dockerfile de arriba | pendiente de build | ⚠️ Pendiente de build |
| CVE-2026-59890 | setuptools | (toolchain) | patch (toolchain) | mismo cambio de Dockerfile de arriba | pendiente de build | ⚠️ Pendiente de build |
| CVE-2026-23949 | jaraco-context | (toolchain, dependencia de setuptools) | patch (toolchain) | mismo cambio de Dockerfile de arriba | pendiente de build | ⚠️ Pendiente de build |

## Ajustes de código por breaking changes

Ninguno de los bumps requirió ajustar código: `paramiko`, `requests` y `python-dotenv` mantuvieron su API pública sin cambios relevantes para el uso que hace este proyecto (cliente SFTP básico, GET/POST HTTP, carga de `.env`). El bump de `pyarrow` (14 → 17) tampoco requirió cambios porque el proyecto no llama a la API de `pyarrow` directamente — solo está presente como dependencia transitiva de `openpyxl`/`pandas`.

## Política Perl / librerías críticas prohibidas

**Bloqueada — se intentó eliminar, Debian lo impide.** Perl viene incluido en la imagen base `python:3.11-slim` (Debian) sin uso funcional alguno en este repo (verificado: sin `.pl`/`.pm`, sin shebangs, sin `apt-get install perl`). Trece CVEs afectan a Perl en esta imagen, dos de ellos críticos (CVSS 9.8 y 9.1), ninguno con parche disponible.

Se probó `apt-get purge -y --auto-remove perl-base perl` en un build real (Cloud Build) y **falló**:

```
Package 'perl' is not installed, so not removed
The following packages will be REMOVED:
  perl-base*
WARNING: The following essential packages will be removed.
This should NOT be done unless you know exactly what you are doing!
  perl-base
E: Essential packages were removed and -y was used without --allow-remove-essential.
```

Debian marca `perl-base` como paquete **esencial** en esta imagen — es una señal real de que removerlo puede romper `dpkg`/`apt` u otras herramientas base del sistema en tiempo de ejecución, no solo un bloqueo burocrático. Forzarlo con `--allow-remove-essential` es posible pero no se probó: el riesgo de dejar el contenedor en un estado roto (sin haber podido validar exhaustivamente qué depende de `perl-base` a nivel de sistema) supera el beneficio de eliminar CVEs que hoy no son explotables porque Perl no se invoca desde el código. Se revirtió el cambio de Dockerfile. Queda documentado como bloqueado.

## Próximos pasos (lo que quedó pendiente)

- [ ] Reconstruir y redesplegar la imagen Docker para que el fix de `pip install --upgrade pip setuptools wheel` tome efecto (resuelve CVE-2026-8643, 6357, 3219, 13346, 2025-8869, 24049, 59890, 23949).
- [ ] Perl queda 🚫 bloqueado — eliminarlo requeriría `--allow-remove-essential` (forzar remoción de un paquete esencial de Debian) o migrar a una imagen base distinta (ej. distroless), ambas opciones de mayor riesgo/esfuerzo que no se aplicaron en esta pasada.
- [ ] Los CVEs de `glibc`, `acl`, `attr`, `tar`, `gzip`, `bzip2`, `sqlite3`, `zlib`, `openldap`, `pam`, `util-linux` (CVE-2026-3184) no tienen parche disponible en Debian a la fecha de este reporte y no son eliminables (son parte del runtime base del sistema) — quedan como riesgo conocido, sin acción posible hasta que Debian libere parche.
- [ ] Los CVEs de `systemd` no aparecen en el escaneo de este repo (`reading`), a diferencia de `reading-csv`/`writing` — no requiere acción aquí.
- [ ] `git add` / `git commit` / `git push` — pendiente, a criterio del usuario tras revisar el diff.

## Verificación ejecutada

- `pip install -r requirements.txt` en un venv limpio: sin conflictos de resolución.
- `pip check`: `No broken requirements found.`
- Import de `src.pipeline` (y transitivamente `src.config`, `src.models`, `src.services`) con variables de entorno mínimas: OK, sin excepciones.
- `pip-audit -r requirements.txt` post-fix: **0 paquetes vulnerables** (antes: 5 paquetes con CVEs conocidos).
