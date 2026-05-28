from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

_QUERY = text("""
    SELECT
        p.numnota       AS numero_nota,
        p.dtfat         AS data_faturamento,
        p.vltotal       AS valor_total,
        cl.cliente      AS cliente,
        cl.cgcent       AS cgcent,
        v.nome          AS vendedor,
        p.numcar        AS id_carregamento,
        c.dtsaida       AS data_saida_carregamento,
        m.nome          AS motorista,
        i.codprod       AS codprod,
        pr.descricao    AS descricao_produto,
        i.qt            AS qt,
        i.pvenda        AS pvenda
    FROM CEDEP.pcpedc p
    LEFT JOIN CEDEP.pcpedi i       ON i.numped   = p.numped
    LEFT JOIN CEDEP.pcclient cl    ON cl.codcli  = p.codcli
    LEFT JOIN CEDEP.pcusuari v     ON v.codusur  = p.codusur
    LEFT JOIN CEDEP.pccarreg c     ON c.numcar   = p.numcar
    LEFT JOIN CEDEP.pcempr m       ON m.matricula = c.codmotorista AND m.tipo = 'M'
    LEFT JOIN CEDEP.pcprodut pr    ON pr.codprod  = i.codprod
    WHERE p.numnota = :numnota
      AND p.dtfat >= ADD_MONTHS(TRUNC(SYSDATE), -24)
      AND p.numped = (
          SELECT numped
          FROM (
              SELECT numped
              FROM CEDEP.pcpedc
              WHERE numnota = :numnota
              ORDER BY dtfat DESC, numped DESC
          )
          WHERE ROWNUM = 1
      )
""")


def _build_response(rows) -> Optional[dict]:
    if not rows:
        return None

    first = rows[0]

    produtos = []
    for row in rows:
        if row.codprod is not None:
            produtos.append({
                "codprod": int(row.codprod),
                "descricao": row.descricao_produto or "",
                "qt": float(row.qt) if row.qt is not None else 0.0,
                "pvenda": float(row.pvenda) if row.pvenda is not None else 0.0,
            })

    return {
        "nota_fiscal": {
            "numero_nota": int(first.numero_nota),
            "data_faturamento": first.data_faturamento,
            "cliente": first.cliente,
            "cgcent": first.cgcent,
            "valor_total": float(first.valor_total) if first.valor_total is not None else None,
            "vendedor": first.vendedor,
            "id_carregamento": int(first.id_carregamento) if first.id_carregamento is not None else None,
            "data_saida_carregamento": first.data_saida_carregamento,
            "motorista": first.motorista,
            "transportadora": None,  # mesma tabela do motorista; distinção não disponível no CEDEP
            "produtos": produtos,
        }
    }


class CarregamentoService:

    @staticmethod
    def get_por_nota(read_engine: Engine, numnota: int) -> Optional[dict]:
        with read_engine.connect() as conn:
            result = conn.execute(_QUERY, {"numnota": numnota})
            rows = result.fetchall()
        return _build_response(rows)


carregamento_service = CarregamentoService()
