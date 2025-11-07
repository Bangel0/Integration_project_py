import streamlit as st
from pages_components.AIApp.ask_to_gemini import ask_to_gemini

# ask_to_gemini()

# app.py
# Requisitos:
#   pip install streamlit google-generativeai
# API Key:
#   export GEMINI_API_KEY="tu_api_key"  (o GOOGLE_API_KEY)
# Nota sobre .rar:
#   Para crear .rar se necesita el binario "rar" (WinRAR/rar de RARLAB) disponible en PATH.
#   Si no está, la app generará .zip como fallback automáticamente.

import os
import re
import io
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import google.generativeai as genai

# ==========================
# Utilidades Generales
# ==========================

def get_api_key() -> Optional[str]:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or st.secrets.get("GEMINI_API_KEY", None)
        or st.secrets.get("GOOGLE_API_KEY", None)
    )

def tool_exists(tool_name: str) -> bool:
    return shutil.which(tool_name) is not None

def sanitize_relative_path(p: str) -> str:
    # Evitar path traversal y rutas absolutas
    p = p.strip().replace("\\", "/")
    p = re.sub(r"^\.+/", "", p)
    p = p.lstrip("/")
    # No permitir subir directorios
    parts = [part for part in p.split("/") if part not in ("", ".", "..")]
    return "/".join(parts)

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Intenta extraer un JSON desde un bloque con backticks o desde el texto completo.
    Espera estructura:
      {
        "project_name": "...",
        "summary": "...",
        "files": [{"path": "...", "content": "...", "executable": false}],
        "post_create_commands": ["..."],
        "run_instructions": "..."
      }
    """
    # Intento 1: Extraer bloque ```json ... ```
    code_block = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if code_block:
        raw = code_block.group(1)
        return json.loads(raw)

    # Intento 2: Extraer bloque ``` ... ```
    code_block_any = re.search(r"```[\w]*\s*(\{[\s\S]*?\})\s*```", text)
    if code_block_any:
        raw = code_block_any.group(1)
        return json.loads(raw)

    # Intento 3: Buscar primera llave y última llave
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = text[start : end + 1]
        return json.loads(raw)

    raise ValueError("No se pudo extraer un JSON válido del contenido del modelo.")

def write_files_from_manifest(base_dir: Path, manifest: Dict[str, Any]) -> List[str]:
    """
    Crea archivos desde el manifest JSON. Devuelve lista de rutas creadas (relativas).
    manifest["files"] = [{ "path": "src/main.py", "content": "...", "executable": false }, ...]
    """
    created_files = []
    files = manifest.get("files", [])
    for f in files:
        rel_path = sanitize_relative_path(f.get("path", ""))
        if not rel_path:
            continue
        content = f.get("content", "")
        p = base_dir / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as out:
            out.write(content)
        if f.get("executable", False):
            try:
                p.chmod(p.stat().st_mode | 0o111)
            except Exception:
                pass
        created_files.append(rel_path)
    return created_files

def create_archive_from_dir(src_dir: Path, out_name: str) -> Path:
    """
    Crea un archivo .rar si el binario 'rar' está disponible; de lo contrario .zip.
    out_name no lleva extensión; se decidirá según disponibilidad.
    """
    rar_available = tool_exists("rar") or tool_exists("Rar") or tool_exists("rar.exe") or tool_exists("Rar.exe")
    if rar_available:
        archive_path = src_dir.parent / f"{out_name}.rar"
        # Ejecutar: rar a -r archive.rar .
        rar_bin = shutil.which("rar") or shutil.which("Rar") or shutil.which("rar.exe") or shutil.which("Rar.exe")
        cmd = [rar_bin, "a", "-r", str(archive_path), "."]
        subprocess.run(cmd, cwd=str(src_dir), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return archive_path
    else:
        # Fallback a ZIP
        archive_path_no_ext = src_dir.parent / out_name
        shutil.make_archive(str(archive_path_no_ext), "zip", root_dir=str(src_dir))
        return archive_path_no_ext.with_suffix(".zip")

def build_prompt(preferences: Dict[str, Any]) -> str:
    """
    Construye el prompt final para el modelo Gemini en español con las selecciones del usuario.
    Pedimos ESTRICTAMENTE un JSON con un esquema específico para facilitar la creación del .rar
    """
    # Descomponer selections
    project_name = preferences.get("project_name")
    descripcion = preferences.get("descripcion")
    alcance = preferences.get("alcance")
    arquitectura = preferences.get("arquitectura")
    idiomas = preferences.get("idiomas", [])
    frameworks = preferences.get("frameworks", [])
    tecnologias = preferences.get("tecnologias", [])
    base_lang = preferences.get("base_lang")
    devcontainers = preferences.get("devcontainers")
    docker_compose = preferences.get("docker_compose")
    package_managers = preferences.get("package_managers", [])
    testing = preferences.get("testing", [])
    linters = preferences.get("linters", [])
    ci_cd = preferences.get("ci_cd", [])
    dbs = preferences.get("dbs", [])
    cloud = preferences.get("cloud", [])
    include_api_example = preferences.get("include_api_example")
    include_docs = preferences.get("include_docs")
    docs_tool = preferences.get("docs_tool")
    license_choice = preferences.get("license_choice")
    py_version = preferences.get("py_version")
    node_version = preferences.get("node_version")
    security_opts = preferences.get("security_opts", [])
    reproducibility = preferences.get("reproducibility", [])
    readme_language = preferences.get("readme_language")
    min_boilerplate = preferences.get("min_boilerplate", True)

    # Prompt con instrucciones estrictas
    prompt = f"""
Eres un asistente que genera boilerplates de proyectos de software de alta calidad, con foco en:
- Mejores prácticas de seguridad, mantenibilidad, reproducibilidad y portabilidad.
- Estructura mínima pero ejecutable (esencia boilerplate), lista para servir como boceto inicial.
- Archivos claros, sin secretos ni credenciales reales.
- Comentarios y README concisos y útiles.

Genera el boilerplate según estas preferencias del usuario:
- Nombre del proyecto: {project_name}
- Descripción: {descripcion}
- Alcance del proyecto: {alcance}
- Arquitectura: {arquitectura}
- Lenguajes objetivo: {", ".join(idiomas) if idiomas else "N/A"}
- Frameworks: {", ".join(frameworks) if frameworks else "N/A"}
- Tecnologías: {", ".join(tecnologias) if tecnologias else "N/A"}
- Base language (idioma de comentarios/README): {base_lang}
- Devcontainers: {devcontainers}
- ¿Incluir docker-compose?: {docker_compose}
- Gestores de dependencias: {", ".join(package_managers) if package_managers else "N/A"}
- Testing: {", ".join(testing) if testing else "N/A"}
- Linters/Formatters: {", ".join(linters) if linters else "N/A"}
- CI/CD: {", ".join(ci_cd) if ci_cd else "N/A"}
- Bases de datos: {", ".join(dbs) if dbs else "N/A"}
- Cloud/Infra: {", ".join(cloud) if cloud else "N/A"}
- ¿Incluir ejemplo de API?: {include_api_example}
- ¿Incluir docs?: {include_docs} (herramienta: {docs_tool})
- Licencia: {license_choice}
- Versiones (Python/Node): Python={py_version}, Node={node_version}
- Opciones de seguridad: {", ".join(security_opts) if security_opts else "N/A"}
- Reproducibilidad: {", ".join(reproducibility) if reproducibility else "N/A"}
- Mantener esencia minimalista pero ejecutable: {min_boilerplate}
- Importante: No incluir archivos gigantes, dependencias pesadas innecesarias ni secretos. Incluir un .env.example si procede.

Requisitos críticos:
1) RESPONDE EXCLUSIVAMENTE con un JSON válido con el siguiente esquema EXACTO:
{{
  "project_name": "string",
  "summary": "string (resumen corto del boilerplate generado y decisiones clave)",
  "files": [
    {{
      "path": "ruta/relativa/archivo.ext",
      "content": "contenido del archivo (texto plano UTF-8)",
      "executable": false
    }}
    // ... más archivos
  ],
  "post_create_commands": [
    "comandos opcionales para preparar/instalar después de descargar"
  ],
  "run_instructions": "instrucciones simples para ejecutar el proyecto localmente"
}}

2) Incluye solo los archivos mínimos necesarios para que el proyecto corra de forma simple y demuestre la estructura:
   - Si Devcontainers = "Usar Dockerfile": incluir un Dockerfile mínimo y opcionalmente docker-compose si se pidió.
   - Si Devcontainers = "Usar devcontainer.json": incluir .devcontainer/devcontainer.json; puedes incluir Dockerfile si corresponde.
3) Si se seleccionó testing/linters/formatters, agrega configuración mínima (por ejemplo: pytest + simple test; ruff/isort/black/eslint/prettier).
4) Si se seleccionó reproducibilidad, fija versiones en requirements.txt/pyproject/lockfiles o package.json.
5) Si se incluyó ejemplo de API, agrega el endpoint más simple (salud o ping) en el framework elegido.
6) Incluir .gitignore, README.{ 'md' if base_lang.lower().startswith('en') else 'md'} y LICENSE con el tipo seleccionado.
7) Si se seleccionó docs, incluir configuración mínima (por ejemplo mkdocs o docusaurus), pero simple.
8) No inventes secretos; usa .env.example con claves de ejemplo. No uses claves reales.
9) Mantén comentarios en el idioma base indicado: {readme_language}.

Resalta mejores prácticas sin sobrecargar el boilerplate. El JSON debe ser el único contenido de tu respuesta.
"""
    return prompt.strip()

def generate_with_gemini(prompt: str, api_key: str, model_name: str = "gemini-1.5-pro") -> str:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.4,
            "top_p": 0.9,
            "max_output_tokens": 18000,
        },
        safety_settings={
            # Config por defecto suele ser suficiente; puedes ajustar si fuese necesario.
        },
    )
    # Puede venir en response.text o en candidates
    if hasattr(response, "text") and response.text:
        return response.text
    # Fallback
    if getattr(response, "candidates", None):
        parts = []
        for cand in response.candidates:
            for part in getattr(cand, "content", []).parts:
                if hasattr(part, "text"):
                    parts.append(part.text)
        return "\n".join(parts).strip()
    raise RuntimeError("La respuesta del modelo no contiene texto utilizable.")

def preview_file_tree(files: List[str]) -> str:
    # Genera una vista simple de arbol
    tree_lines = []
    paths = sorted(files)
    for p in paths:
        depth = p.count("/")
        indent = "  " * depth
        name = p.split("/")[-1]
        tree_lines.append(f"{indent}- {name} ({p})")
    return "\n".join(tree_lines)

# ==========================
# UI Streamlit
# ==========================

st.set_page_config(page_title="Generador de Boilerplates (Gemini)", page_icon="🧪", layout="wide")
st.title("Generador de Boilerplates con Gemini")
st.caption("Crea scaffolds mínimos, seguros y reproducibles según tus parámetros. Entrega en .rar (o .zip si no hay 'rar').")

api_key = get_api_key()
if not api_key:
    st.error("Falta la API Key. Define la variable de entorno GEMINI_API_KEY o GOOGLE_API_KEY, o agrega en st.secrets.")
    st.stop()

with st.sidebar:
    st.header("Configuración Global")
    model_choice = st.selectbox("Modelo Gemini", ["gemini-2.5-pro", "gemini-2.5-flash"], index=0)
    st.info("La creación de .rar requiere tener instalado el binario 'rar'. Si no está, se generará .zip.")

with st.form("boilerplate_form"):
    st.subheader("Metadatos del Proyecto")
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Nombre del proyecto", placeholder="mi-proyecto-ejemplo", value="mi-proyecto-ejemplo")
        arquitectura = st.selectbox("Arquitectura", ["Monolito", "Microservicios", "CLI", "Librería", "Servicio Web"], index=0)
        base_lang = st.selectbox("Idioma base de comentarios/README", ["Español", "English"], index=0)
        readme_language = base_lang
        license_choice = st.selectbox("Licencia", ["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Unlicense"], index=0)
        include_api_example = st.checkbox("Incluir ejemplo de API mínima", value=True)
    with col2:
        descripcion = st.text_area("Descripción corta", placeholder="Breve descripción del objetivo del proyecto.", height=90)
        alcance = st.text_area("Alcance del proyecto", placeholder="Alcance, requisitos, límites, supuestos...", height=90)
        include_docs = st.checkbox("Incluir docs", value=False)
        docs_tool = st.selectbox("Herramienta de docs", ["mkdocs", "docusaurus", "none"], index=0 if include_docs else 2)

    st.subheader("Stack Tecnológico")
    col3, col4 = st.columns(2)
    with col3:
        idiomas = st.multiselect(
            "Lenguajes",
            ["Python", "JavaScript", "TypeScript", "Go", "Java", "C#", "Rust"],
            default=["Python"]
        )
        frameworks = st.multiselect(
            "Frameworks",
            [
                # Python
                "FastAPI", "Flask", "Django",
                # JS/TS
                "Express", "NestJS", "Next.js", "React", "Vue", "Angular", "SvelteKit",
                # Otros
                "Spring Boot", ".NET Minimal API", "Gin (Go)", "Fiber (Go)"
            ],
            default=["FastAPI"]
        )
        tecnologias = st.multiselect(
            "Tecnologías/Servicios",
            ["GraphQL", "REST", "gRPC", "WebSockets", "OpenAPI", "Celery/RQ", "Redis", "Kafka", "RabbitMQ"]
        )
        dbs = st.multiselect("Bases de datos", ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis"], default=["SQLite"])
    with col4:
        cloud = st.multiselect("Cloud/Infra", ["Docker", "Kubernetes", "Terraform", "AWS", "GCP", "Azure"])
        devcontainers = st.selectbox("Incluir Devcontainers", ["Usar Dockerfile", "Usar devcontainer.json", "No incluir"], index=0)
        docker_compose = st.checkbox("Incluir docker-compose", value=True)
        package_managers = st.multiselect(
            "Gestores de dependencias",
            ["pip", "Poetry", "uv", "npm", "pnpm", "yarn"],
            default=["pip"]
        )
        reproducibility = st.multiselect(
            "Reproducibilidad",
            ["Pin de versiones", "Lockfiles", "Versionado SemVer", "Dependabot/Renovate"],
            default=["Pin de versiones", "Lockfiles", "Versionado SemVer"]
        )

    st.subheader("Calidad, Seguridad y Testing")
    col5, col6 = st.columns(2)
    with col5:
        testing = st.multiselect(
            "Testing",
            ["pytest", "unittest", "jest", "vitest", "go test", "JUnit", "pytest-cov"],
            default=["pytest"]
        )
        linters = st.multiselect(
            "Linters/Formatters",
            ["ruff", "flake8", "black", "isort", "eslint", "prettier", "pylint"],
            default=["ruff", "black", "isort"]
        )
        ci_cd = st.multiselect("CI/CD", ["GitHub Actions", "GitLab CI", "CircleCI"], default=["GitHub Actions"])
    with col6:
        security_opts = st.multiselect(
            "Seguridad",
            ["pre-commit", "bandit (Python)", "safety (Python)", "dotenv .env.example", "SAST básico"],
            default=["pre-commit", "dotenv .env.example"]
        )
        py_version = st.text_input("Versión objetivo de Python", value="3.11")
        node_version = st.text_input("Versión objetivo de Node", value="20")
        min_boilerplate = st.checkbox("Mantener esencia minimalista (mínimos ejecutables)", value=True)

    st.form_submit_button("Generar Boilerplate", type="primary")

# Si se envió el formulario, procesamos
if "generated_manifest" not in st.session_state:
    st.session_state.generated_manifest = None
if "archive_bytes" not in st.session_state:
    st.session_state.archive_bytes = None
if "archive_name" not in st.session_state:
    st.session_state.archive_name = None
if "archive_mime" not in st.session_state:
    st.session_state.archive_mime = None
if "created_files" not in st.session_state:
    st.session_state.created_files = []

if st.session_state.get("boilerplate_form"):
    pass  # Streamlit maneja el form internamente

# Reconstruir preferencias desde widgets actuales
preferences = {
    "project_name": project_name,
    "descripcion": descripcion,
    "alcance": alcance,
    "arquitectura": arquitectura,
    "idiomas": idiomas,
    "frameworks": frameworks,
    "tecnologias": tecnologias,
    "base_lang": base_lang,
    "devcontainers": devcontainers,
    "docker_compose": docker_compose,
    "package_managers": package_managers,
    "testing": testing,
    "linters": linters,
    "ci_cd": ci_cd,
    "dbs": dbs,
    "cloud": cloud,
    "include_api_example": include_api_example,
    "include_docs": include_docs,
    "docs_tool": docs_tool,
    "license_choice": license_choice,
    "py_version": py_version,
    "node_version": node_version,
    "security_opts": security_opts,
    "reproducibility": reproducibility,
    "readme_language": readme_language,
    "min_boilerplate": min_boilerplate,
}

# Botón separado para ejecutar generación (para más control visual)
generate = st.button("Generar con Gemini y preparar descarga", type="primary")

if generate:
    with st.spinner("Generando boilerplate con Gemini..."):
        try:
            prompt = build_prompt(preferences)
            raw_text = generate_with_gemini(prompt, api_key=api_key, model_name=model_choice)
            manifest = extract_json_from_text(raw_text)

            # Crear estructura temporal
            tmp_root = Path(tempfile.mkdtemp(prefix="boilerplate_"))
            proj_dir = tmp_root / sanitize_relative_path(manifest.get("project_name", project_name or "proyecto"))
            proj_dir.mkdir(parents=True, exist_ok=True)

            created_files = write_files_from_manifest(proj_dir, manifest)

            # Crear archivo comprimido: .rar si está "rar", si no .zip
            try:
                archive_path = create_archive_from_dir(proj_dir, out_name=proj_dir.name)
                archive_bytes = Path(archive_path).read_bytes()
                archive_name = archive_path.name
                mime = "application/x-rar-compressed" if archive_path.suffix.lower() == ".rar" else "application/zip"

                st.session_state.generated_manifest = manifest
                st.session_state.created_files = created_files
                st.session_state.archive_bytes = archive_bytes
                st.session_state.archive_name = archive_name
                st.session_state.archive_mime = mime
            finally:
                # Limpieza del directorio temporal
                try:
                    shutil.rmtree(tmp_root, ignore_errors=True)
                except Exception:
                    pass

        except Exception as e:
            st.error(f"Ocurrió un error durante la generación: {e}")

# Vista previa y descarga
if st.session_state.generated_manifest:
    manifest = st.session_state.generated_manifest
    st.success("Boilerplate generado correctamente.")
    with st.expander("Resumen generado por el modelo"):
        st.write(manifest.get("summary", ""))
    with st.expander("Árbol de archivos (vista previa)"):
        if st.session_state.created_files:
            st.code(preview_file_tree(st.session_state.created_files), language="text")
        else:
            st.write("No se reportan archivos en el manifest.")
    with st.expander("Instrucciones de post-creación"):
        cmds = manifest.get("post_create_commands", [])
        if cmds:
            st.code("\n".join(cmds), language="bash")
        else:
            st.write("No se especificaron comandos.")
    with st.expander("Instrucciones para ejecutar"):
        st.write(manifest.get("run_instructions", "No provistas."))

    # Aviso sobre .rar/.zip
    if st.session_state.archive_mime == "application/zip":
        st.info("No se detectó el binario 'rar' en el sistema. Se generó un archivo .zip como alternativa.")

    st.download_button(
        label=f"Descargar {st.session_state.archive_name}",
        data=st.session_state.archive_bytes,
        file_name=st.session_state.archive_name,
        mime=st.session_state.archive_mime
    )

    st.caption("Consejo: Revisa los archivos generados (especialmente dependencias y scripts) antes de producción.")




