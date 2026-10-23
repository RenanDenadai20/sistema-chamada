"""
db.py — Camada de banco de dados SQLite para o Sistema de Chamada.
Inicializa o banco, semeia as 26 turmas fixas e expõe funções CRUD.
"""

import sys
import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Quando executado como .exe standalone (PyInstaller),
    # a pasta 'dados' e o arquivo 'dados.db' devem ficar permanentemente junto ao executável!
    BASE_DIR = Path(sys.executable).parent
    TEMPLATE_DIR = Path(sys._MEIPASS) / "dados_template" if hasattr(sys, "_MEIPASS") else None
else:
    # Quando executado em desenvolvimento via script Python
    BASE_DIR = Path(__file__).parent
    TEMPLATE_DIR = None

DADOS_DIR = BASE_DIR / "dados"
BACKUPS_DIR = DADOS_DIR / "backups"
DB_PATH = DADOS_DIR / "dados.db"

DADOS_DIR.mkdir(exist_ok=True, parents=True)
BACKUPS_DIR.mkdir(exist_ok=True, parents=True)


# ---------------------------------------------------------------------------
# Turmas fixas
# ---------------------------------------------------------------------------
_TURMAS_INFO = []
_DIAS_INFO = [("SEG", "Segunda"), ("QUA", "Quarta"), ("SEX", "Sexta")]
_HORARIOS_INFO = [
    ("08H00", "08:00", "09:00", "kids"),
    ("09H10", "09:10", "10:10", "teens"),
    ("14H00", "14:00", "15:00", "kids"),
    ("15H10", "15:10", "16:10", "teens"),
    ("16H20", "16:20", "17:20", "kids"),
    ("17H20", "17:20", "18:20", "teens"),
]
for _dia_cod, _dia_nome in _DIAS_INFO:
    for _hor_cod, _inicio, _fim, _faixa in _HORARIOS_INFO:
        _TURMAS_INFO.append({
            "id": f"INFO-{_dia_cod}-{_hor_cod}",
            "curso": "Informática",
            "dia_semana": _dia_nome,
            "horario_inicio": _inicio,
            "horario_fim": _fim,
            "faixa_etaria": _faixa,
            "nome": f"Informática — {_dia_nome} {_inicio}–{_fim} ({_faixa.capitalize()})",
        })

_TURMAS_ROBO = []
_DIAS_ROBO = [("TER", "Terça"), ("QUI", "Quinta")]
_HORARIOS_ROBO = [
    ("08H00", "08:00", "09:30"),
    ("09H30", "09:30", "11:00"),
    ("14H00", "14:00", "15:30"),
    ("15H30", "15:30", "17:00"),
]
for _dia_cod, _dia_nome in _DIAS_ROBO:
    for _hor_cod, _inicio, _fim in _HORARIOS_ROBO:
        _TURMAS_ROBO.append({
            "id": f"ROBO-{_dia_cod}-{_hor_cod}",
            "curso": "Robótica",
            "dia_semana": _dia_nome,
            "horario_inicio": _inicio,
            "horario_fim": _fim,
            "faixa_etaria": None,
            "nome": f"Robótica — {_dia_nome} {_inicio}–{_fim}",
        })

ALL_TURMAS = _TURMAS_INFO + _TURMAS_ROBO


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS turmas (
    id              TEXT PRIMARY KEY,
    curso           TEXT NOT NULL,
    dia_semana      TEXT NOT NULL,
    horario_inicio  TEXT NOT NULL,
    horario_fim     TEXT NOT NULL,
    faixa_etaria    TEXT,
    nome            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alunos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    data_nascimento TEXT,
    genero          TEXT,
    curso           TEXT NOT NULL DEFAULT 'Informática',
    observacao      TEXT DEFAULT '',
    criado_em       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS aluno_turma (
    aluno_id    INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    turma_id    TEXT    NOT NULL REFERENCES turmas(id) ON DELETE CASCADE,
    PRIMARY KEY (aluno_id, turma_id)
);

CREATE TABLE IF NOT EXISTS chamadas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    turma_id    TEXT NOT NULL REFERENCES turmas(id),
    data        TEXT NOT NULL,
    UNIQUE(turma_id, data)
);

CREATE TABLE IF NOT EXISTS presencas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chamada_id  INTEGER NOT NULL REFERENCES chamadas(id) ON DELETE CASCADE,
    aluno_id    INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    presente    INTEGER NOT NULL DEFAULT 0,
    observacao  TEXT DEFAULT '',
    UNIQUE(chamada_id, aluno_id)
);

CREATE TABLE IF NOT EXISTS ocorrencias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id    INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    descricao   TEXT NOT NULL,
    data        TEXT NOT NULL DEFAULT (date('now','localtime')),
    criado_em   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


def _garantir_banco_inicial():
    """Garante que o banco de dados inicial exista com os dados completos ao rodar standalone."""
    try:
        if not DB_PATH.exists() or DB_PATH.stat().st_size == 0:
            # 1. Se existir template embutido no pacote PyInstaller, copia para a pasta permanente
            if TEMPLATE_DIR and (TEMPLATE_DIR / "dados.db").exists():
                shutil.copy2(str(TEMPLATE_DIR / "dados.db"), str(DB_PATH))
                return

            # 2. Se executado no Desktop ou outra pasta, tenta puxar do projeto original se existir
            candidatos = [
                Path(r"C:\Users\Usuario\Desktop\renan e joao\chamada\sistema-chamada\dados\dados.db"),
                Path(r"C:\Users\Usuario\Desktop\chamada\sistema-chamada\dados\dados.db"),
                Path(r"C:\Users\Usuario\Desktop\dados\dados.db"),
            ]
            for cand in candidatos:
                if cand.exists() and cand.stat().st_size > 0:
                    try:
                        if cand.resolve() != DB_PATH.resolve():
                            shutil.copy2(str(cand), str(DB_PATH))
                            return
                    except Exception:
                        pass
    except Exception:
        pass


def init_db():
    """Cria as tabelas e semeia as turmas fixas."""
    _garantir_banco_inicial()
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
        for t in ALL_TURMAS:
            conn.execute(
                """INSERT OR IGNORE INTO turmas
                   (id, curso, dia_semana, horario_inicio, horario_fim, faixa_etaria, nome)
                   VALUES (:id, :curso, :dia_semana, :horario_inicio, :horario_fim, :faixa_etaria, :nome)""",
                t,
            )
        conn.commit()



# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------
def fazer_backup(motivo: str = "") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo = f"_{motivo}" if motivo else ""
    dest = BACKUPS_DIR / f"dados_{ts}{sufixo}.db"
    shutil.copy2(str(DB_PATH), str(dest))
    return dest


# ---------------------------------------------------------------------------
# Turmas
# ---------------------------------------------------------------------------
def listar_turmas(curso: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM turmas"
    params: list = []
    if curso and curso != "Todos":
        sql += " WHERE curso = ?"
        params.append(curso)
    sql += " ORDER BY curso, dia_semana, horario_inicio"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_turma(turma_id: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM turmas WHERE id=?", (turma_id,)).fetchone()


# ---------------------------------------------------------------------------
# Alunos — CRUD
# ---------------------------------------------------------------------------
def listar_alunos(
    busca: str = "",
    curso: str = "",
    turma_id: str = "",
    apenas_pendentes: bool = False,
) -> list[sqlite3.Row]:
    sql = """
        SELECT DISTINCT a.*
        FROM alunos a
        LEFT JOIN aluno_turma at2 ON at2.aluno_id = a.id
        WHERE 1=1
    """
    params: list = []
    if busca:
        sql += " AND a.nome LIKE ?"
        params.append(f"%{busca}%")
    if curso and curso != "Todos":
        if curso == "Ambos":
            sql += " AND a.curso = 'Ambos'"
        else:
            sql += " AND (a.curso = ? OR a.curso = 'Ambos')"
            params.append(curso)
    if turma_id:
        sql += " AND at2.turma_id = ?"
        params.append(turma_id)
    if apenas_pendentes:
        sql += " AND (a.data_nascimento IS NULL OR a.data_nascimento = '' OR a.genero IS NULL OR a.genero = '')"
    sql += " ORDER BY a.nome"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_aluno(aluno_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alunos WHERE id=?", (aluno_id,)).fetchone()


def get_aluno_por_nome(nome: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM alunos WHERE LOWER(TRIM(nome))=LOWER(TRIM(?))", (nome,)
        ).fetchone()


def criar_aluno(nome: str, data_nascimento: str = "", genero: str = "",
                curso: str = "Informática", observacao: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO alunos (nome, data_nascimento, genero, curso, observacao) VALUES (?,?,?,?,?)",
            (nome.strip(), data_nascimento, genero, curso, observacao),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore


def atualizar_aluno(aluno_id: int, nome: str, data_nascimento: str,
                    genero: str, curso: str, observacao: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE alunos SET nome=?, data_nascimento=?, genero=?, curso=?, observacao=?
               WHERE id=?""",
            (nome.strip(), data_nascimento, genero, curso, observacao, aluno_id),
        )
        conn.commit()


def excluir_aluno(aluno_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM alunos WHERE id=?", (aluno_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Matrículas (aluno ↔ turma)
# ---------------------------------------------------------------------------
def turmas_do_aluno(aluno_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT t.* FROM turmas t
               JOIN aluno_turma at2 ON at2.turma_id = t.id
               WHERE at2.aluno_id = ?
               ORDER BY t.curso, t.dia_semana, t.horario_inicio""",
            (aluno_id,),
        ).fetchall()


def matricular_aluno(aluno_id: int, turma_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
            (aluno_id, turma_id),
        )
        conn.commit()


def desmatricular_aluno(aluno_id: int, turma_id: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM aluno_turma WHERE aluno_id=? AND turma_id=?",
            (aluno_id, turma_id),
        )
        conn.commit()


def set_turmas_aluno(aluno_id: int, turma_ids: list[str]):
    with get_conn() as conn:
        conn.execute("DELETE FROM aluno_turma WHERE aluno_id=?", (aluno_id,))
        for tid in turma_ids:
            conn.execute(
                "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
                (aluno_id, tid),
            )
        conn.commit()


def alunos_da_turma(turma_id: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT a.* FROM alunos a
               JOIN aluno_turma at2 ON at2.aluno_id = a.id
               WHERE at2.turma_id = ?
               ORDER BY a.nome""",
            (turma_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# Chamada / Presença
# ---------------------------------------------------------------------------
def get_chamada(turma_id: str, data: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM chamadas WHERE turma_id=? AND data=?",
            (turma_id, data),
        ).fetchone()


def criar_ou_obter_chamada(turma_id: str, data: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM chamadas WHERE turma_id=? AND data=?", (turma_id, data)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO chamadas (turma_id, data) VALUES (?,?)", (turma_id, data)
        )
        conn.commit()
        return cur.lastrowid  # type: ignore


def salvar_presencas(chamada_id: int, presencas: list[dict]):
    """presencas = [{"aluno_id": int, "presente": 0|1, "observacao": str}]"""
    with get_conn() as conn:
        conn.execute("DELETE FROM presencas WHERE chamada_id=?", (chamada_id,))
        conn.executemany(
            "INSERT INTO presencas (chamada_id, aluno_id, presente, observacao) VALUES (:chamada_id, :aluno_id, :presente, :observacao)",
            [{"chamada_id": chamada_id, **p} for p in presencas],
        )
        conn.commit()


def get_presencas(chamada_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM presencas WHERE chamada_id=?", (chamada_id,)
        ).fetchall()


def historico_aluno(aluno_id: int, turma_id: str | None = None) -> list[sqlite3.Row]:
    sql = """
        SELECT c.turma_id, c.data, p.presente, p.observacao, t.nome as turma_nome
        FROM presencas p
        JOIN chamadas c ON c.id = p.chamada_id
        JOIN turmas t ON t.id = c.turma_id
        WHERE p.aluno_id = ?
    """
    params: list = [aluno_id]
    if turma_id:
        sql += " AND c.turma_id = ?"
        params.append(turma_id)
    sql += " ORDER BY c.data DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def frequencia_aluno_mes(aluno_id: int, mes: int, ano: int) -> dict:
    """Retorna frequência separada por curso para o aluno no mês/ano."""
    result = {}
    with get_conn() as conn:
        for curso in ("Informática", "Robótica"):
            rows = conn.execute(
                """SELECT p.presente
                   FROM presencas p
                   JOIN chamadas c ON c.id = p.chamada_id
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE p.aluno_id = ?
                     AND t.curso = ?
                     AND strftime('%m', c.data) = ?
                     AND strftime('%Y', c.data) = ?""",
                (aluno_id, curso, f"{mes:02d}", str(ano)),
            ).fetchall()
            if rows:
                total = len(rows)
                presentes = sum(r["presente"] for r in rows)
                result[curso] = {"total": total, "presentes": presentes,
                                 "pct": round(presentes / total * 100, 1)}
    return result


# ---------------------------------------------------------------------------
# Estatísticas mensais
# ---------------------------------------------------------------------------
def alunos_por_quadrimestre(ano: int) -> list[dict]:
    """
    Retorna o número de alunos por curso a cada 4 meses:
    - 1º Quadrimestre (Janeiro a Abril)
    - 2º Quadrimestre (Maio a Agosto)
    - 3º Quadrimestre (Setembro a Dezembro)
    """
    ano_str = str(ano)
    quads_def = [
        ("1º Quadrimestre (Jan–Abr)", ["01", "02", "03", "04"]),
        ("2º Quadrimestre (Mai–Ago)", ["05", "06", "07", "08"]),
        ("3º Quadrimestre (Set–Dez)", ["09", "10", "11", "12"]),
    ]
    resultado = []
    with get_conn() as conn:
        total_cad = conn.execute(
            """SELECT
               SUM(CASE WHEN curso='Informática' THEN 1 ELSE 0 END) as info,
               SUM(CASE WHEN curso='Robótica' THEN 1 ELSE 0 END) as robo,
               SUM(CASE WHEN curso='Ambos' THEN 1 ELSE 0 END) as ambos,
               COUNT(*) as total
               FROM alunos"""
        ).fetchone()

        for nome_q, meses in quads_def:
            placeholders = ",".join("?" for _ in meses)
            rows_presenca = conn.execute(
                f"""SELECT a.curso, COUNT(DISTINCT a.id) as qtd
                    FROM alunos a
                    JOIN presencas p ON p.aluno_id = a.id
                    JOIN chamadas c ON c.id = p.chamada_id
                    WHERE strftime('%Y', c.data) = ? AND strftime('%m', c.data) IN ({placeholders})
                    GROUP BY a.curso""",
                [ano_str] + meses,
            ).fetchall()

            ativos_q = {r["curso"]: r["qtd"] for r in rows_presenca}
            teve_aulas = sum(ativos_q.values()) > 0

            resultado.append({
                "quadrimestre": nome_q,
                "info_ativos": ativos_q.get("Informática", 0),
                "robo_ativos": ativos_q.get("Robótica", 0),
                "ambos_ativos": ativos_q.get("Ambos", 0),
                "total_ativos": sum(ativos_q.values()),
                "info_cadastrados": total_cad["info"] or 0,
                "robo_cadastrados": total_cad["robo"] or 0,
                "ambos_cadastrados": total_cad["ambos"] or 0,
                "total_cadastrados": total_cad["total"] or 0,
                "teve_aulas": teve_aulas,
            })
    return resultado


def estatisticas_mes(mes: int, ano: int) -> dict:
    mes_str = f"{mes:02d}"
    ano_str = str(ano)
    with get_conn() as conn:
        # ---- 1. Horas por mês separadas por curso e total -----------------
        horas_curso = {}
        for c in ("Informática", "Robótica"):
            row = conn.execute(
                """SELECT SUM(
                       (strftime('%H', t.horario_fim) - strftime('%H', t.horario_inicio)) * 60 +
                       (strftime('%M', t.horario_fim) - strftime('%M', t.horario_inicio))
                   ) as minutos,
                   COUNT(DISTINCT c.id) as total_aulas
                   FROM chamadas c
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) = ? AND strftime('%Y', c.data) = ?""",
                (c, mes_str, ano_str),
            ).fetchone()
            m = row["minutos"] or 0
            horas_curso[c] = {
                "minutos": m,
                "horas": round(m / 60, 1),
                "aulas": row["total_aulas"] or 0,
            }

        total_min = horas_curso["Informática"]["minutos"] + horas_curso["Robótica"]["minutos"]
        total_horas = round(total_min / 60, 1)

        # ---- 2. Cursos oferecidos mensalmente ------------------------------
        cursos_oferecidos = {}
        for c in ("Informática", "Robótica"):
            tot_turmas = conn.execute("SELECT COUNT(*) as qtd FROM turmas WHERE curso=?", (c,)).fetchone()["qtd"]
            turmas_com_aulas = conn.execute(
                """SELECT COUNT(DISTINCT c.turma_id) as turmas_ativas,
                          COUNT(c.id) as aulas_dadas
                   FROM chamadas c
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) = ? AND strftime('%Y', c.data) = ?""",
                (c, mes_str, ano_str),
            ).fetchone()
            matriculas_curso = conn.execute(
                """SELECT COUNT(*) as qtd FROM aluno_turma at2
                   JOIN turmas t ON t.id = at2.turma_id
                   WHERE t.curso = ?""", (c,),
            ).fetchone()["qtd"]

            cursos_oferecidos[c] = {
                "total_turmas": tot_turmas,
                "turmas_ativas": turmas_com_aulas["turmas_ativas"] or 0,
                "aulas_no_mes": turmas_com_aulas["aulas_dadas"] or 0,
                "matriculas": matriculas_curso,
                "horas": horas_curso[c]["horas"],
                "minutos": horas_curso[c]["minutos"],
            }

        # ---- 3. Presença mensal dos alunos por curso ----------------------
        presenca_mensal_cursos = {}
        freq = {}
        for c in ("Informática", "Robótica"):
            row = conn.execute(
                """SELECT
                       SUM(CASE WHEN p.presente = 1 THEN 1 ELSE 0 END) as presentes,
                       SUM(CASE WHEN p.presente = 0 THEN 1 ELSE 0 END) as ausentes,
                       COUNT(p.id) as total
                   FROM presencas p
                   JOIN chamadas c ON c.id = p.chamada_id
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) = ? AND strftime('%Y', c.data) = ?""",
                (c, mes_str, ano_str),
            ).fetchone()
            tot = row["total"] or 0
            pres = row["presentes"] or 0
            aus = row["ausentes"] or 0
            pct = round(pres / tot * 100, 1) if tot > 0 else None
            presenca_mensal_cursos[c] = {
                "presentes": pres,
                "ausentes": aus,
                "total": tot,
                "pct": pct,
            }
            freq[c] = pct

        # ---- 4. Presença detalhada por idade e sexo ------------------------
        presencas_detalhadas = conn.execute(
            """SELECT a.data_nascimento, a.genero, p.presente, t.curso
               FROM presencas p
               JOIN chamadas c ON c.id = p.chamada_id
               JOIN turmas t ON t.id = c.turma_id
               JOIN alunos a ON a.id = p.aluno_id
               WHERE strftime('%m', c.data) = ? AND strftime('%Y', c.data) = ?""",
            (mes_str, ano_str),
        ).fetchall()

        presenca_por_sexo = {
            "Masculino": {"presentes": 0, "ausentes": 0, "total": 0, "pct": None},
            "Feminino": {"presentes": 0, "ausentes": 0, "total": 0, "pct": None},
        }
        presenca_por_idade = {}

        hoje = datetime.now().date()
        for r in presencas_detalhadas:
            gen = r["genero"]
            pres = r["presente"]
            if gen in presenca_por_sexo:
                if pres == 1:
                    presenca_por_sexo[gen]["presentes"] += 1
                else:
                    presenca_por_sexo[gen]["ausentes"] += 1
                presenca_por_sexo[gen]["total"] += 1

            if r["data_nascimento"]:
                try:
                    d = datetime.strptime(r["data_nascimento"], "%Y-%m-%d").date()
                    idade = hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
                    if idade not in presenca_por_idade:
                        presenca_por_idade[idade] = {
                            "Masculino": {"presentes": 0, "total": 0, "pct": None},
                            "Feminino": {"presentes": 0, "total": 0, "pct": None},
                            "total_presentes": 0,
                            "total_registros": 0,
                            "pct": None,
                        }
                    item_id = presenca_por_idade[idade]
                    if gen in ("Masculino", "Feminino"):
                        item_id[gen]["total"] += 1
                        if pres == 1:
                            item_id[gen]["presentes"] += 1
                    item_id["total_registros"] += 1
                    if pres == 1:
                        item_id["total_presentes"] += 1
                except Exception:
                    pass

        # Calcula porcentagens de sexo
        for g in presenca_por_sexo:
            tg = presenca_por_sexo[g]["total"]
            if tg > 0:
                presenca_por_sexo[g]["pct"] = round(presenca_por_sexo[g]["presentes"] / tg * 100, 1)

        # Calcula porcentagens de idade
        for ida, dados in presenca_por_idade.items():
            for g in ("Masculino", "Feminino"):
                tg = dados[g]["total"]
                if tg > 0:
                    dados[g]["pct"] = round(dados[g]["presentes"] / tg * 100, 1)
            tot_ida = dados["total_registros"]
            if tot_ida > 0:
                dados["pct"] = round(dados["total_presentes"] / tot_ida * 100, 1)

        # ---- 5. Contagem de alunos por tipo --------------------------------
        contagem = conn.execute(
            """SELECT
               SUM(CASE WHEN curso='Informática' THEN 1 ELSE 0 END) as so_info,
               SUM(CASE WHEN curso='Robótica' THEN 1 ELSE 0 END) as so_robo,
               SUM(CASE WHEN curso='Ambos' THEN 1 ELSE 0 END) as ambos
               FROM alunos"""
        ).fetchone()

        # ---- 6. Gênero geral por curso -------------------------------------
        genero = conn.execute(
            """SELECT curso, genero, COUNT(*) as qtd
               FROM alunos
               WHERE genero IS NOT NULL AND genero != ''
               GROUP BY curso, genero"""
        ).fetchall()

        # ---- 7. Matrículas gerais ------------------------------------------
        matriculas = conn.execute(
            """SELECT t.curso, COUNT(*) as qtd
               FROM aluno_turma at2
               JOIN turmas t ON t.id = at2.turma_id
               GROUP BY t.curso"""
        ).fetchall()

        # ---- 8. Distribuição de idades cadastrais ---------------------------
        idades_rows = conn.execute(
            """SELECT a.data_nascimento, a.genero, a.curso
               FROM alunos a
               WHERE a.data_nascimento IS NOT NULL AND a.data_nascimento != ''"""
        ).fetchall()

        alunos_rows = conn.execute("SELECT * FROM alunos").fetchall()

    # Quadrimestres do ano
    quads = alunos_por_quadrimestre(ano)

    return {
        "total_minutos": total_min,
        "total_horas": total_horas,
        "horas_curso": horas_curso,
        "cursos_oferecidos": cursos_oferecidos,
        "presenca_mensal_cursos": presenca_mensal_cursos,
        "presenca_por_sexo": presenca_por_sexo,
        "presenca_por_idade": presenca_por_idade,
        "quadrimestres": quads,
        "contagem": dict(contagem),
        "genero": [dict(r) for r in genero],
        "freq": freq,
        "matriculas": [dict(r) for r in matriculas],
        "idades_rows": [dict(r) for r in idades_rows],
        "alunos_rows": [dict(r) for r in alunos_rows],
        "mes": mes,
        "ano": ano,
        "limite_freq": 75.0,
    }



def alunos_freq_baixa(mes: int, ano: int, limite: float = 75.0) -> list[dict]:
    mes_str = f"{mes:02d}"
    ano_str = str(ano)
    resultado = []
    with get_conn() as conn:
        alunos = conn.execute("SELECT * FROM alunos").fetchall()
        for a in alunos:
            cursos_verificar = []
            if a["curso"] in ("Informática", "Ambos"):
                cursos_verificar.append("Informática")
            if a["curso"] in ("Robótica", "Ambos"):
                cursos_verificar.append("Robótica")
            for curso in cursos_verificar:
                rows = conn.execute(
                    """SELECT p.presente
                       FROM presencas p
                       JOIN chamadas c ON c.id = p.chamada_id
                       JOIN turmas t ON t.id = c.turma_id
                       WHERE p.aluno_id = ? AND t.curso = ?
                         AND strftime('%m', c.data) = ?
                         AND strftime('%Y', c.data) = ?""",
                    (a["id"], curso, mes_str, ano_str),
                ).fetchall()
                if rows:
                    total = len(rows)
                    presentes = sum(r["presente"] for r in rows)
                    pct = presentes / total * 100
                    if pct < limite:
                        # pega turmas do aluno daquele curso
                        turmas = conn.execute(
                            """SELECT t.nome FROM turmas t
                               JOIN aluno_turma at2 ON at2.turma_id = t.id
                               WHERE at2.aluno_id = ? AND t.curso = ?""",
                            (a["id"], curso),
                        ).fetchall()
                        turmas_str = ", ".join(r["nome"] for r in turmas)
                        resultado.append({
                            "aluno_id": a["id"],
                            "nome": a["nome"],
                            "curso": curso,
                            "turmas": turmas_str,
                            "pct": round(pct, 1),
                            "presentes": presentes,
                            "total": total,
                        })
    return resultado


_NOMES_TRIMESTRES = {
    1: "1º Trimestre (Jan – Mar)",
    2: "2º Trimestre (Abr – Jun)",
    3: "3º Trimestre (Jul – Set)",
    4: "4º Trimestre (Out – Dez)",
}

_MESES_DO_TRIMESTRE = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}


def alunos_freq_baixa_trimestre(trimestre: int, ano: int, limite: float = 75.0) -> list[dict]:
    meses = _MESES_DO_TRIMESTRE.get(trimestre, [7, 8, 9])
    meses_str = [f"{m:02d}" for m in meses]
    ano_str = str(ano)
    resultado = []
    with get_conn() as conn:
        alunos = conn.execute("SELECT * FROM alunos").fetchall()
        for a in alunos:
            cursos_verificar = []
            if a["curso"] in ("Informática", "Ambos"):
                cursos_verificar.append("Informática")
            if a["curso"] in ("Robótica", "Ambos"):
                cursos_verificar.append("Robótica")
            for curso in cursos_verificar:
                rows = conn.execute(
                    """SELECT p.presente
                       FROM presencas p
                       JOIN chamadas c ON c.id = p.chamada_id
                       JOIN turmas t ON t.id = c.turma_id
                       WHERE p.aluno_id = ? AND t.curso = ?
                         AND strftime('%m', c.data) IN (?, ?, ?)
                         AND strftime('%Y', c.data) = ?""",
                    (a["id"], curso, meses_str[0], meses_str[1], meses_str[2], ano_str),
                ).fetchall()
                if rows:
                    total = len(rows)
                    presentes = sum(r["presente"] for r in rows)
                    pct = presentes / total * 100
                    if pct < limite:
                        turmas = conn.execute(
                            """SELECT t.nome FROM turmas t
                               JOIN aluno_turma at2 ON at2.turma_id = t.id
                               WHERE at2.aluno_id = ? AND t.curso = ?""",
                            (a["id"], curso),
                        ).fetchall()
                        turmas_str = ", ".join(r["nome"] for r in turmas)
                        resultado.append({
                            "aluno_id": a["id"],
                            "nome": a["nome"],
                            "curso": curso,
                            "turmas": turmas_str,
                            "pct": round(pct, 1),
                            "presentes": presentes,
                            "total": total,
                        })
    return resultado


def estatisticas_trimestre(trimestre: int, ano: int) -> dict:
    """Calcula estatísticas trimestrais consolidadas e mês a mês para o trimestre indicado (1 a 4)."""
    meses = _MESES_DO_TRIMESTRE.get(trimestre, [7, 8, 9])
    meses_str = [f"{m:02d}" for m in meses]
    ano_str = str(ano)

    # 1. Estatísticas de cada mês individual do trimestre
    dados_mensais = {}
    atendimentos_acumulados = 0
    for m in meses:
        s_m = estatisticas_mes(m, ano)
        dados_mensais[m] = s_m
        # soma atendimentos/matrículas ativas dos cursos no mês
        ci_m = s_m["cursos_oferecidos"].get("Informática", {}).get("matriculas", 0)
        cr_m = s_m["cursos_oferecidos"].get("Robótica", {}).get("matriculas", 0)
        # alunos únicos com chamada ou matriculados ativos no mês
        cnt_m = s_m["contagem"]
        tot_m = (cnt_m.get("so_info") or 0) + (cnt_m.get("so_robo") or 0) + (cnt_m.get("ambos") or 0)
        atendimentos_acumulados += tot_m

    with get_conn() as conn:
        # 2. Horas totais por curso no trimestre
        horas_curso = {}
        for c in ("Informática", "Robótica"):
            row = conn.execute(
                """SELECT SUM(
                       (strftime('%H', t.horario_fim) - strftime('%H', t.horario_inicio)) * 60 +
                       (strftime('%M', t.horario_fim) - strftime('%M', t.horario_inicio))
                   ) as minutos,
                   COUNT(DISTINCT c.id) as total_aulas
                   FROM chamadas c
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) IN (?, ?, ?) AND strftime('%Y', c.data) = ?""",
                (c, meses_str[0], meses_str[1], meses_str[2], ano_str),
            ).fetchone()
            m_min = row["minutos"] or 0
            horas_curso[c] = {
                "minutos": m_min,
                "horas": round(m_min / 60, 1),
                "aulas": row["total_aulas"] or 0,
            }

        total_min = horas_curso["Informática"]["minutos"] + horas_curso["Robótica"]["minutos"]
        total_horas = round(total_min / 60, 1)

        # 3. Cursos oferecidos no trimestre
        cursos_oferecidos = {}
        for c in ("Informática", "Robótica"):
            tot_turmas = conn.execute("SELECT COUNT(*) as qtd FROM turmas WHERE curso=?", (c,)).fetchone()["qtd"]
            turmas_com_aulas = conn.execute(
                """SELECT COUNT(DISTINCT c.turma_id) as turmas_ativas,
                          COUNT(c.id) as aulas_dadas
                   FROM chamadas c
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) IN (?, ?, ?) AND strftime('%Y', c.data) = ?""",
                (c, meses_str[0], meses_str[1], meses_str[2], ano_str),
            ).fetchone()
            matriculas_curso = conn.execute(
                """SELECT COUNT(*) as qtd FROM aluno_turma at2
                   JOIN turmas t ON t.id = at2.turma_id
                   WHERE t.curso = ?""", (c,),
            ).fetchone()["qtd"]

            cursos_oferecidos[c] = {
                "total_turmas": tot_turmas,
                "turmas_ativas": turmas_com_aulas["turmas_ativas"] or 0,
                "aulas_no_periodo": turmas_com_aulas["aulas_dadas"] or 0,
                "matriculas": matriculas_curso,
                "horas": horas_curso[c]["horas"],
                "minutos": horas_curso[c]["minutos"],
            }

        # 4. Presença dos alunos por curso no trimestre
        presenca_cursos = {}
        freq = {}
        for c in ("Informática", "Robótica"):
            row = conn.execute(
                """SELECT
                       SUM(CASE WHEN p.presente = 1 THEN 1 ELSE 0 END) as presentes,
                       SUM(CASE WHEN p.presente = 0 THEN 1 ELSE 0 END) as ausentes,
                       COUNT(p.id) as total
                   FROM presencas p
                   JOIN chamadas c ON c.id = p.chamada_id
                   JOIN turmas t ON t.id = c.turma_id
                   WHERE t.curso = ? AND strftime('%m', c.data) IN (?, ?, ?) AND strftime('%Y', c.data) = ?""",
                (c, meses_str[0], meses_str[1], meses_str[2], ano_str),
            ).fetchone()
            tot = row["total"] or 0
            pres = row["presentes"] or 0
            aus = row["ausentes"] or 0
            pct = round(pres / tot * 100, 1) if tot > 0 else None
            presenca_cursos[c] = {
                "presentes": pres,
                "ausentes": aus,
                "total": tot,
                "pct": pct,
            }
            freq[c] = pct

        # 5. Presença detalhada por idade e sexo no trimestre
        presencas_detalhadas = conn.execute(
            """SELECT a.data_nascimento, a.genero, p.presente, t.curso
               FROM presencas p
               JOIN chamadas c ON c.id = p.chamada_id
               JOIN turmas t ON t.id = c.turma_id
               JOIN alunos a ON a.id = p.aluno_id
               WHERE strftime('%m', c.data) IN (?, ?, ?) AND strftime('%Y', c.data) = ?""",
            (meses_str[0], meses_str[1], meses_str[2], ano_str),
        ).fetchall()

        presenca_por_sexo = {
            "Masculino": {"presentes": 0, "ausentes": 0, "total": 0, "pct": None},
            "Feminino": {"presentes": 0, "ausentes": 0, "total": 0, "pct": None},
        }
        presenca_por_idade = {}

        hoje = datetime.now().date()
        for r in presencas_detalhadas:
            gen = r["genero"]
            pres = r["presente"]
            if gen in presenca_por_sexo:
                if pres == 1:
                    presenca_por_sexo[gen]["presentes"] += 1
                else:
                    presenca_por_sexo[gen]["ausentes"] += 1
                presenca_por_sexo[gen]["total"] += 1

            if r["data_nascimento"]:
                try:
                    d = datetime.strptime(r["data_nascimento"], "%Y-%m-%d").date()
                    idade = hoje.year - d.year - ((hoje.month, hoje.day) < (d.month, d.day))
                    if idade not in presenca_por_idade:
                        presenca_por_idade[idade] = {
                            "Masculino": {"presentes": 0, "total": 0, "pct": None},
                            "Feminino": {"presentes": 0, "total": 0, "pct": None},
                            "total_presentes": 0,
                            "total_registros": 0,
                            "pct": None,
                        }
                    item_id = presenca_por_idade[idade]
                    if gen in ("Masculino", "Feminino"):
                        item_id[gen]["total"] += 1
                        if pres == 1:
                            item_id[gen]["presentes"] += 1
                    item_id["total_registros"] += 1
                    if pres == 1:
                        item_id["total_presentes"] += 1
                except Exception:
                    pass

        for g in presenca_por_sexo:
            tg = presenca_por_sexo[g]["total"]
            if tg > 0:
                presenca_por_sexo[g]["pct"] = round(presenca_por_sexo[g]["presentes"] / tg * 100, 1)

        for ida, dados in presenca_por_idade.items():
            for g in ("Masculino", "Feminino"):
                tg = dados[g]["total"]
                if tg > 0:
                    dados[g]["pct"] = round(dados[g]["presentes"] / tg * 100, 1)
            tot_ida = dados["total_registros"]
            if tot_ida > 0:
                dados["pct"] = round(dados["total_presentes"] / tot_ida * 100, 1)

        # 6. Alunos beneficiários únicos atendidos com chamadas no trimestre
        beneficiarios_rows = conn.execute(
            """SELECT DISTINCT a.id, a.nome, a.genero, a.curso, a.data_nascimento
               FROM presencas p
               JOIN chamadas c ON c.id = p.chamada_id
               JOIN alunos a ON a.id = p.aluno_id
               WHERE strftime('%m', c.data) IN (?, ?, ?) AND strftime('%Y', c.data) = ?""",
            (meses_str[0], meses_str[1], meses_str[2], ano_str),
        ).fetchall()

        beneficiarios_genero = {"Masculino": 0, "Feminino": 0, "Outro": 0}
        beneficiarios_curso = {"Informática": 0, "Robótica": 0, "Ambos": 0}
        for b in beneficiarios_rows:
            gen = b["genero"] or "Outro"
            if gen in beneficiarios_genero:
                beneficiarios_genero[gen] += 1
            cur = b["curso"] or "Ambos"
            if cur in beneficiarios_curso:
                beneficiarios_curso[cur] += 1

        # 7. Contagem geral cadastrada
        contagem = conn.execute(
            """SELECT
               SUM(CASE WHEN curso='Informática' THEN 1 ELSE 0 END) as so_info,
               SUM(CASE WHEN curso='Robótica' THEN 1 ELSE 0 END) as so_robo,
               SUM(CASE WHEN curso='Ambos' THEN 1 ELSE 0 END) as ambos
               FROM alunos"""
        ).fetchone()

        genero = conn.execute(
            """SELECT curso, genero, COUNT(*) as qtd
               FROM alunos
               WHERE genero IS NOT NULL AND genero != ''
               GROUP BY curso, genero"""
        ).fetchall()

        matriculas = conn.execute(
            """SELECT t.curso, COUNT(*) as qtd
               FROM aluno_turma at2
               JOIN turmas t ON t.id = at2.turma_id
               GROUP BY t.curso"""
        ).fetchall()

        idades_rows = conn.execute(
            """SELECT a.data_nascimento, a.genero, a.curso
               FROM alunos a
               WHERE a.data_nascimento IS NOT NULL AND a.data_nascimento != ''"""
        ).fetchall()

        alunos_rows = conn.execute("SELECT * FROM alunos").fetchall()

    quads = alunos_por_quadrimestre(ano)

    return {
        "trimestre": trimestre,
        "trimestre_nome": _NOMES_TRIMESTRES.get(trimestre, f"{trimestre}º Trimestre"),
        "meses": meses,
        "ano": ano,
        "dados_mensais": dados_mensais,
        "total_minutos": total_min,
        "total_horas": total_horas,
        "horas_curso": horas_curso,
        "cursos_oferecidos": cursos_oferecidos,
        "presenca_cursos": presenca_cursos,
        "presenca_por_sexo": presenca_por_sexo,
        "presenca_por_idade": presenca_por_idade,
        "beneficiarios_unicos_total": len(beneficiarios_rows),
        "beneficiarios_genero": beneficiarios_genero,
        "beneficiarios_curso": beneficiarios_curso,
        "atendimentos_acumulados": atendimentos_acumulados,
        "contagem": dict(contagem),
        "genero": [dict(r) for r in genero],
        "freq": freq,
        "matriculas": [dict(r) for r in matriculas],
        "idades_rows": [dict(r) for r in idades_rows],
        "alunos_rows": [dict(r) for r in alunos_rows],
        "quadrimestres": quads,
        "limite_freq": 75.0,
    }



# ---------------------------------------------------------------------------
# Ocorrências
# ---------------------------------------------------------------------------
def listar_nomes_alunos() -> list[dict]:
    """Retorna lista de (id, nome, curso, turmas) de todos os alunos para autocomplete."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, nome, curso FROM alunos ORDER BY nome"
        ).fetchall()
    resultado = []
    for r in rows:
        turmas = turmas_do_aluno(r["id"])
        turmas_str = "; ".join(
            t["nome"].split("—")[1].strip() if "—" in t["nome"] else t["nome"]
            for t in turmas
        ) if turmas else "Sem turma"
        resultado.append({
            "id": r["id"],
            "nome": r["nome"],
            "curso": r["curso"],
            "turmas": turmas_str,
        })
    return resultado


def criar_ocorrencia(aluno_id: int, descricao: str, data: str = "") -> int:
    """Registra uma nova ocorrência para o aluno. data deve ser 'AAAA-MM-DD' ou vazio para hoje."""
    with get_conn() as conn:
        if data:
            cur = conn.execute(
                "INSERT INTO ocorrencias (aluno_id, descricao, data) VALUES (?,?,?)",
                (aluno_id, descricao.strip(), data),
            )
        else:
            cur = conn.execute(
                "INSERT INTO ocorrencias (aluno_id, descricao) VALUES (?,?)",
                (aluno_id, descricao.strip()),
            )
        conn.commit()
        return cur.lastrowid  # type: ignore


def listar_ocorrencias(busca: str = "", aluno_id: int | None = None) -> list[dict]:
    """Lista ocorrências ordenadas da mais recente para a mais antiga."""
    sql = """
        SELECT o.id, o.descricao, o.data, o.criado_em,
               a.id as aluno_id, a.nome as aluno_nome, a.curso
        FROM ocorrencias o
        JOIN alunos a ON a.id = o.aluno_id
        WHERE 1=1
    """
    params: list = []
    if aluno_id is not None:
        sql += " AND o.aluno_id = ?"
        params.append(aluno_id)
    if busca:
        sql += " AND (a.nome LIKE ? OR o.descricao LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])
    sql += " ORDER BY o.data DESC, o.criado_em DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    resultado = []
    for r in rows:
        turmas = turmas_do_aluno(r["aluno_id"])
        turmas_str = "; ".join(
            t["nome"].split("—")[1].strip() if "—" in t["nome"] else t["nome"]
            for t in turmas
        ) if turmas else "Sem turma"
        resultado.append({
            "id": r["id"],
            "descricao": r["descricao"],
            "data": r["data"],
            "criado_em": r["criado_em"],
            "aluno_id": r["aluno_id"],
            "aluno_nome": r["aluno_nome"],
            "curso": r["curso"],
            "turmas": turmas_str,
        })
    return resultado


def excluir_ocorrencia(ocorrencia_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM ocorrencias WHERE id=?", (ocorrencia_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Importação e Parsing Estruturado (.txt)
# ---------------------------------------------------------------------------
import re


def parse_data_nascimento(data_str: str) -> str:
    """Converte formatos de data (ex: DD/MM/AAAA, DD-MM-AAAA) para ISO AAAA-MM-DD."""
    if not data_str:
        return ""
    data_str = data_str.strip()
    # Verifica se já está em AAAA-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", data_str):
        return data_str

    # Formatos comuns: DD/MM/AAAA, D/M/AAAA, DD-MM-AAAA
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", data_str)
    if m:
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = datetime(ano, mes, dia).date()
            return d.strftime("%Y-%m-%d")
        except ValueError:
            return ""
    return ""


def parse_header_turma(header: str) -> dict:
    """
    Identifica automaticamente dia da semana, horário inicial, final,
    curso sugerido e nome formatado a partir do cabeçalho de uma turma.
    Exemplos:
      - 'SEGUNDA_8H_9H'
      - 'SEGUNDA_9H_10H'
      - 'TERCA_8H_9H'
      - 'QUINTA_15H30_17H'
      - 'ROBOTICA_TERCA_08:00_09:30'
    """
    raw = header.strip()
    norm = raw.upper()

    # 1. Dia da semana
    dias_map = [
        ("SEGUNDA", "Segunda"), ("SEG", "Segunda"),
        ("TERÇA", "Terça"), ("TERCA", "Terça"), ("TER", "Terça"),
        ("QUARTA", "Quarta"), ("QUA", "Quarta"),
        ("QUINTA", "Quinta"), ("QUI", "Quinta"),
        ("SEXTA", "Sexta"), ("SEX", "Sexta"),
        ("SÁBADO", "Sábado"), ("SABADO", "Sábado"), ("SAB", "Sábado"),
        ("DOMINGO", "Domingo"), ("DOM", "Domingo"),
    ]
    dia_semana = ""
    for token, nome_dia in dias_map:
        if re.search(r"(?:^|_|\b)" + token + r"(?:$|_|\b)", norm):
            dia_semana = nome_dia
            break

    # 2. Curso sugerido
    curso = ""
    if "ROBO" in norm:
        curso = "Robótica"
    elif "INFO" in norm:
        curso = "Informática"
    elif dia_semana in ("Terça", "Quinta"):
        curso = "Robótica"
    elif dia_semana in ("Segunda", "Quarta", "Sexta"):
        curso = "Informática"
    else:
        curso = "Informática"

    # 3. Horários inicial e final
    # Procura padrão range: ex: 8H_9H, 8H00_9H00, 15H30_17H, 08:00_09:30, 8_9
    h_inicio, h_fim = "", ""
    range_regex = r"(\d{1,2})(?:[Hh:](\d{2}))?(?:\s*[Hh])?\s*(?:_|-|–|—|ÀS|AS|A|TO)\s*(\d{1,2})(?:[Hh:](\d{2}))?(?:\s*[Hh])?"
    m_range = re.search(range_regex, norm)
    if m_range:
        h1 = int(m_range.group(1))
        m1 = int(m_range.group(2) or 0)
        h2 = int(m_range.group(3))
        m2 = int(m_range.group(4) or 0)
        h_inicio = f"{h1:02d}:{m1:02d}"
        h_fim = f"{h2:02d}:{m2:02d}"
    else:
        # Tenta achar horários avulsos
        single_regex = r"(\d{1,2})(?:[Hh:](\d{2})|[Hh])"
        singles = re.findall(single_regex, norm)
        if len(singles) >= 2:
            h1, m1 = int(singles[0][0]), int(singles[0][1] or 0)
            h2, m2 = int(singles[1][0]), int(singles[1][1] or 0)
            h_inicio = f"{h1:02d}:{m1:02d}"
            h_fim = f"{h2:02d}:{m2:02d}"
        elif len(singles) == 1:
            h1, m1 = int(singles[0][0]), int(singles[0][1] or 0)
            h_inicio = f"{h1:02d}:{m1:02d}"
            h_fim = f"{(h1 + 1):02d}:{m1:02d}"

    # Faixa ou nome
    horario_str = f"{h_inicio}–{h_fim}" if (h_inicio and h_fim) else (h_inicio or raw)
    dia_str = dia_semana or "Turma"
    nome_turma = f"{curso} — {dia_str} {horario_str}"

    # ID sugerido único
    prefix_c = "ROBO" if curso == "Robótica" else "INFO"
    prefix_d = dia_semana[:3].upper() if dia_semana else "TUR"
    prefix_h = h_inicio.replace(":", "H") if h_inicio else "GEN"
    id_sugerido = f"{prefix_c}-{prefix_d}-{prefix_h}"

    return {
        "header_original": raw,
        "dia_semana": dia_semana or "Segunda",
        "horario_inicio": h_inicio or "08:00",
        "horario_fim": h_fim or "09:00",
        "curso": curso,
        "nome_turma": nome_turma,
        "id_sugerido": id_sugerido,
    }


def buscar_turma_correspondente(dia_semana: str, horario_inicio: str, horario_fim: str = "") -> sqlite3.Row | None:
    """Busca a turma existente no banco mais compatível com o dia e horário informados."""
    turmas = listar_turmas()
    if not turmas:
        return None

    dia_lower = dia_semana.lower().replace("á", "a").replace("ç", "c")

    def _d_eq(t_dia: str) -> bool:
        return t_dia.lower().replace("á", "a").replace("ç", "c") == dia_lower

    # 1. Combinação exata de dia, início e fim
    for t in turmas:
        if _d_eq(t["dia_semana"]) and t["horario_inicio"] == horario_inicio:
            if not horario_fim or t["horario_fim"] == horario_fim:
                return t

    # 2. Combinação de dia e mesmo início exato
    for t in turmas:
        if _d_eq(t["dia_semana"]) and t["horario_inicio"] == horario_inicio:
            return t

    # 3. Combinação de dia e mesma hora de início (ex: 09:00 vs 09:10)
    if ":" in horario_inicio:
        h_hora = horario_inicio.split(":")[0] + ":"
        for t in turmas:
            if _d_eq(t["dia_semana"]) and t["horario_inicio"].startswith(h_hora):
                return t

    return None


def criar_turma(id_turma: str, curso: str, dia_semana: str,
                horario_inicio: str, horario_fim: str,
                faixa_etaria: str | None = None, nome: str = "") -> str:
    """Cria ou atualiza uma turma no banco."""
    if not nome:
        faixa = f" ({faixa_etaria.capitalize()})" if faixa_etaria else ""
        nome = f"{curso} — {dia_semana} {horario_inicio}–{horario_fim}{faixa}"
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO turmas
               (id, curso, dia_semana, horario_inicio, horario_fim, faixa_etaria, nome)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id_turma, curso, dia_semana, horario_inicio, horario_fim, faixa_etaria, nome),
        )
        conn.commit()
    return id_turma


def parse_arquivo_importacao(conteudo: str) -> dict:
    """
    Analisa o conteúdo de um arquivo .txt de importação.
    Suporta formato estruturado em blocos:
        SEGUNDA_8H_9H {
        NOME;DATA;GENERO;
        }
    E também mantém compatibilidade com formato simples linha por linha.
    """
    # Procura blocos NOME { CONTEUDO }
    block_pattern = re.compile(r"([^{}\r\n]+)\s*\{([^}]*)\}", re.MULTILINE | re.DOTALL)
    matches = list(block_pattern.finditer(conteudo))

    if matches:
        turmas_detectadas = []
        todos_alunos_count = 0

        for m in matches:
            header_str = m.group(1).strip()
            corpo_str = m.group(2)

            info = parse_header_turma(header_str)
            turma_existente = buscar_turma_correspondente(
                info["dia_semana"], info["horario_inicio"], info["horario_fim"]
            )

            alunos_turma = []
            for linha in corpo_str.splitlines():
                linha_limpa = linha.strip().rstrip(";")
                if not linha_limpa or linha_limpa.startswith("#"):
                    continue
                partes = [p.strip() for p in linha.split(";")]
                nome = partes[0].strip() if len(partes) > 0 else ""
                if not nome:
                    continue

                data_raw = partes[1].strip() if len(partes) > 1 else ""
                genero_raw = partes[2].strip() if len(partes) > 2 else ""

                data_iso = parse_data_nascimento(data_raw)

                # Normalização de gênero
                genero = ""
                if genero_raw:
                    g_low = genero_raw.lower()
                    if g_low.startswith("f"):
                        genero = "Feminino"
                    elif g_low.startswith("m"):
                        genero = "Masculino"
                    else:
                        genero = genero_raw

                aluno_db = get_aluno_por_nome(nome)
                ja_cadastrado = aluno_db is not None

                alunos_turma.append({
                    "nome": nome,
                    "data_nascimento_raw": data_raw,
                    "data_nascimento_iso": data_iso,
                    "genero": genero,
                    "ja_cadastrado": ja_cadastrado,
                    "aluno_id": aluno_db["id"] if aluno_db else None,
                })
                todos_alunos_count += 1

            turmas_detectadas.append({
                "header_original": header_str,
                "info": info,
                "turma_existente_id": turma_existente["id"] if turma_existente else None,
                "turma_existente_nome": turma_existente["nome"] if turma_existente else None,
                "alunos": alunos_turma,
            })

        return {
            "formato": "estruturado",
            "turmas": turmas_detectadas,
            "total_turmas": len(turmas_detectadas),
            "total_alunos": todos_alunos_count,
        }

    # Se não há blocos {}, processa no formato simples legado
    linhas = [l.strip().rstrip(";") for l in conteudo.splitlines() if l.strip().rstrip(";")]
    alunos_simples = []
    for l in linhas:
        partes = [p.strip() for p in l.split(";")]
        nome = partes[0] if partes else ""
        if not nome or nome.startswith("#"):
            continue
        data_raw = partes[1] if len(partes) > 1 else ""
        genero_raw = partes[2] if len(partes) > 2 else ""
        data_iso = parse_data_nascimento(data_raw)
        genero = "Feminino" if genero_raw.lower().startswith("f") else ("Masculino" if genero_raw.lower().startswith("m") else genero_raw)
        aluno_db = get_aluno_por_nome(nome)

        alunos_simples.append({
            "nome": nome,
            "data_nascimento_raw": data_raw,
            "data_nascimento_iso": data_iso,
            "genero": genero,
            "ja_cadastrado": aluno_db is not None,
            "aluno_id": aluno_db["id"] if aluno_db else None,
        })

    return {
        "formato": "simples",
        "turmas": [],
        "alunos_simples": alunos_simples,
        "total_turmas": 0,
        "total_alunos": len(alunos_simples),
    }


def executar_importacao_estruturada(turmas_config: list[dict], atualizar_dados_cadastrais: bool = True) -> dict:
    """
    Executa a importação estruturada para cada turma configurada.
    turmas_config é uma lista de dicionários contendo:
        - 'turma_id': ID da turma de destino (existente ou nova)
        - 'criar_turma_nova': bool
        - 'nova_turma_dados': dict com dados caso precise criar (id, curso, dia_semana, horario_inicio, horario_fim, nome)
        - 'alunos': list[dict] com nome, data_nascimento_iso, genero
    """
    fazer_backup("antes_importacao_estruturada")

    stats = {
        "turmas_processadas": 0,
        "alunos_criados": 0,
        "alunos_vinculados": 0,
        "alunos_atualizados": 0,
        "detalhes_turmas": [],
    }

    with get_conn() as conn:
        for t_cfg in turmas_config:
            turma_id = t_cfg["turma_id"]

            # Cria nova turma se for o caso
            if t_cfg.get("criar_turma_nova"):
                nt = t_cfg["nova_turma_dados"]
                conn.execute(
                    """INSERT OR REPLACE INTO turmas
                       (id, curso, dia_semana, horario_inicio, horario_fim, faixa_etaria, nome)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (nt["id"], nt["curso"], nt["dia_semana"], nt["horario_inicio"], nt["horario_fim"], None, nt["nome"]),
                )
                turma_id = nt["id"]

            # Obtém curso da turma
            turma_row = conn.execute("SELECT * FROM turmas WHERE id=?", (turma_id,)).fetchone()
            curso_turma = turma_row["curso"] if turma_row else "Informática"
            turma_nome = turma_row["nome"] if turma_row else turma_id

            criados_turma = 0
            vinculados_turma = 0

            for a in t_cfg["alunos"]:
                nome = a["nome"].strip()
                data_nasc = a.get("data_nascimento_iso") or ""
                genero = a.get("genero") or ""

                aluno_row = conn.execute(
                    "SELECT * FROM alunos WHERE LOWER(TRIM(nome))=LOWER(TRIM(?))", (nome,)
                ).fetchone()

                if aluno_row:
                    aluno_id = aluno_row["id"]
                    # Atualiza dados cadastrais se solicitado
                    if atualizar_dados_cadastrais:
                        novo_nasc = data_nasc if data_nasc else aluno_row["data_nascimento"]
                        novo_genero = genero if genero else aluno_row["genero"]
                        # Atualiza curso se estiver em Informática e Robótica
                        novo_curso = aluno_row["curso"]
                        if curso_turma and aluno_row["curso"] != curso_turma and aluno_row["curso"] != "Ambos":
                            novo_curso = "Ambos"

                        conn.execute(
                            """UPDATE alunos SET data_nascimento=?, genero=?, curso=?
                               WHERE id=?""",
                            (novo_nasc, novo_genero, novo_curso, aluno_id),
                        )
                        stats["alunos_atualizados"] += 1

                    # Matricula na turma
                    conn.execute(
                        "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
                        (aluno_id, turma_id),
                    )
                    vinculados_turma += 1
                    stats["alunos_vinculados"] += 1
                else:
                    cur = conn.execute(
                        "INSERT INTO alunos (nome, data_nascimento, genero, curso, observacao) VALUES (?,?,?,?,?)",
                        (nome, data_nasc, genero, curso_turma, ""),
                    )
                    new_id = cur.lastrowid
                    conn.execute(
                        "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
                        (new_id, turma_id),
                    )
                    criados_turma += 1
                    stats["alunos_criados"] += 1

            stats["turmas_processadas"] += 1
            stats["detalhes_turmas"].append({
                "turma_id": turma_id,
                "turma_nome": turma_nome,
                "criados": criados_turma,
                "vinculados": vinculados_turma,
                "total": len(t_cfg["alunos"]),
            })

        conn.commit()

    return stats


def importar_alunos_txt(caminho: str) -> tuple[list[str], list[str]]:
    """Lê .txt e retorna (novos, ja_existentes)."""
    with open(caminho, encoding="utf-8", errors="replace") as f:
        linhas = f.read()
    nomes = [n.strip().rstrip(";").strip() for n in linhas.split("\n") if n.strip().rstrip(";").strip()]
    novos, existentes = [], []
    for nome in nomes:
        if get_aluno_por_nome(nome):
            existentes.append(nome)
        else:
            novos.append(nome)
    return novos, existentes


def importar_alunos_para_turma(caminho: str, turma_id: str) -> dict:
    """
    Importa nomes de um .txt para uma turma específica.
    Retorna stats: criados, atualizados_para_ambos, ja_na_turma, erros.
    """
    turma = get_turma(turma_id)
    if not turma:
        return {"erro": "Turma não encontrada"}
    curso_turma = turma["curso"]
    with open(caminho, encoding="utf-8", errors="replace") as f:
        linhas = f.read()
    nomes = [n.strip().rstrip(";").strip() for n in linhas.split("\n") if n.strip().rstrip(";").strip()]

    criados, atualizados, ja_na_turma = [], [], []
    with get_conn() as conn:
        for nome in nomes:
            aluno = get_aluno_por_nome(nome)
            if aluno:
                # verifica se já está nessa turma
                ja = conn.execute(
                    "SELECT 1 FROM aluno_turma WHERE aluno_id=? AND turma_id=?",
                    (aluno["id"], turma_id),
                ).fetchone()
                if ja:
                    ja_na_turma.append(nome)
                    continue
                # matricula na nova turma
                conn.execute(
                    "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
                    (aluno["id"], turma_id),
                )
                # atualiza curso para "Ambos" se necessário
                if aluno["curso"] != curso_turma and aluno["curso"] != "Ambos":
                    conn.execute("UPDATE alunos SET curso='Ambos' WHERE id=?", (aluno["id"],))
                atualizados.append(nome)
            else:
                cur = conn.execute(
                    "INSERT INTO alunos (nome, curso) VALUES (?,?)",
                    (nome, curso_turma),
                )
                new_id = cur.lastrowid
                conn.execute(
                    "INSERT OR IGNORE INTO aluno_turma (aluno_id, turma_id) VALUES (?,?)",
                    (new_id, turma_id),
                )
                criados.append(nome)
        conn.commit()
    return {"criados": criados, "atualizados": atualizados, "ja_na_turma": ja_na_turma}


def formatar_header_turma(turma: sqlite3.Row | dict) -> str:
    """Gera um cabeçalho identificador legível e compatível com o importador (ex: SEGUNDA_8H_9H)."""
    d = dict(turma)
    dia = d.get("dia_semana", "TURMA").upper()
    dia = dia.replace("Ç", "C").replace("Ã", "A").replace("Á", "A").replace("É", "E")

    def _fmt_h(h_str):
        if not h_str:
            return ""
        partes = str(h_str).split(":")
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        return f"{h}H" if m == 0 else f"{h}H{m:02d}"

    ini_str = _fmt_h(d.get("horario_inicio", ""))
    fim_str = _fmt_h(d.get("horario_fim", ""))

    if ini_str and fim_str:
        return f"{dia}_{ini_str}_{fim_str}"
    elif ini_str:
        return f"{dia}_{ini_str}"
    return dia


def formatar_data_br(data_str: str | None) -> str:
    """Converte data YYYY-MM-DD para DD/MM/AAAA para exportação."""
    if not data_str:
        return ""
    data_str = str(data_str).strip()
    if re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
        return data_str
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", data_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return data_str


def exportar_alunos_txt(caminho: str, turma_id: str | None = None) -> dict:
    """
    Exporta turmas e alunos no formato estruturado idêntico ao modelo de importação:

    SEGUNDA_8H_9H {
    NOME DO ALUNO;DATA DE NASCIMENTO;GÊNERO;
    }
    """
    ordem_dias = {
        "segunda": 1, "terça": 2, "terca": 2, "quarta": 3,
        "quinta": 4, "sexta": 5, "sábado": 6, "sabado": 6, "domingo": 7
    }

    with get_conn() as conn:
        if turma_id:
            turmas = conn.execute("SELECT * FROM turmas WHERE id=?", (turma_id,)).fetchall()
        else:
            todas = conn.execute("SELECT * FROM turmas").fetchall()
            turmas = sorted(
                todas,
                key=lambda t: (ordem_dias.get((t["dia_semana"] or "").lower(), 99), t["horario_inicio"] or "")
            )

        total_turmas = 0
        total_alunos = 0
        linhas_exportadas = []

        for t in turmas:
            header = formatar_header_turma(t)
            alunos = conn.execute(
                """SELECT a.* FROM alunos a
                   JOIN aluno_turma at ON a.id = at.aluno_id
                   WHERE at.turma_id = ?
                   ORDER BY a.nome COLLATE NOCASE""",
                (t["id"],),
            ).fetchall()

            linhas_exportadas.append(f"{header} {{\n")
            for a in alunos:
                nome = a["nome"].strip()
                data_br = formatar_data_br(a["data_nascimento"])
                gen = (a["genero"] or "").strip()
                linhas_exportadas.append(f"{nome};{data_br};{gen};\n")
                total_alunos += 1
            linhas_exportadas.append("}\n\n")
            total_turmas += 1

        # Se não filtrou por turma, verifica se há alunos sem turma vinculada
        if not turma_id:
            sem_turma = conn.execute(
                """SELECT a.* FROM alunos a
                   WHERE a.id NOT IN (SELECT aluno_id FROM aluno_turma)
                   ORDER BY a.nome COLLATE NOCASE"""
            ).fetchall()
            if sem_turma:
                linhas_exportadas.append("ALUNOS_SEM_TURMA {\n")
                for a in sem_turma:
                    nome = a["nome"].strip()
                    data_br = formatar_data_br(a["data_nascimento"])
                    gen = (a["genero"] or "").strip()
                    linhas_exportadas.append(f"{nome};{data_br};{gen};\n")
                    total_alunos += 1
                linhas_exportadas.append("}\n\n")
                total_turmas += 1

    with open(caminho, "w", encoding="utf-8") as f:
        f.writelines(linhas_exportadas)

    return {
        "total_turmas": total_turmas,
        "total_alunos": total_alunos,
        "caminho": caminho,
    }


def aluno_cadastro_completo(aluno: sqlite3.Row | dict) -> bool:
    d = dict(aluno)
    return bool(d.get("data_nascimento")) and bool(d.get("genero"))


def turmas_por_dia_semana(dia_semana: str, curso: str | None = None) -> list[sqlite3.Row]:
    """Retorna todas as turmas cadastradas para determinado dia da semana, ordenadas por horário."""
    dia_norm = dia_semana.strip().lower().replace("ç", "c").replace("á", "a").replace("ã", "a")
    todas = listar_turmas(curso=curso)
    res = []
    for t in todas:
        t_dia = (t["dia_semana"] or "").strip().lower().replace("ç", "c").replace("á", "a").replace("ã", "a")
        if t_dia == dia_norm:
            res.append(t)
    return sorted(res, key=lambda x: x["horario_inicio"] or "")


def status_chamadas_mes(ano: int, mes: int) -> dict[str, dict]:
    """
    Retorna um dicionário mapeando f'{turma_id}_{data}' -> dados da chamada realizada
    para todas as chamadas do mês/ano informado em uma única consulta SQL.
    """
    prefix = f"{ano:04d}-{mes:02d}"
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT c.id, c.turma_id, c.data,
                      COUNT(p.id) as total_alunos,
                      SUM(CASE WHEN p.presente = 1 THEN 1 ELSE 0 END) as total_presentes,
                      SUM(CASE WHEN p.presente = 0 THEN 1 ELSE 0 END) as total_ausentes
               FROM chamadas c
               LEFT JOIN presencas p ON c.id = p.chamada_id
               WHERE c.data LIKE ?
               GROUP BY c.id, c.turma_id, c.data""",
            (f"{prefix}%",),
        ).fetchall()

    resultado = {}
    for r in rows:
        key = f"{r['turma_id']}_{r['data']}"
        resultado[key] = {
            "chamada_id": r["id"],
            "turma_id": r["turma_id"],
            "data": r["data"],
            "total_alunos": r["total_alunos"],
            "total_presentes": r["total_presentes"] or 0,
            "total_ausentes": r["total_ausentes"] or 0,
        }
    return resultado


