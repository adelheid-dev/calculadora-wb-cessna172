# Calculadora de Peso, Balanceamento e CG — Cessna 172S

Calcula peso, momentos e CG nas condições de **Rampa → Decolagem → ZFW**.
Verifica geometricamente se cada ponto fica **estritamente dentro** do envelope
do POH, com validação dupla (Shapely + Matplotlib Path). Também confere todas
as limitações de estação e de peso e exporta um relatório `.txt`.

> ⚠️ O Peso Básico Vazio e o braço em `wb/config.py` são um exemplo
> (1663 lb @ 40,6 in). Substitua pelos dados da ficha de pesagem da sua aeronave.
> Esta é uma ferramenta de estudo e conferência, e não substitui o POH/AFM.

## Dados do Cessna 172S (POH, Seções 2 e 6)

| Item | Valor |
|---|---|
| MTOW / Rampa (Normal) | 2550 / 2558 lb |
| MTOW / Rampa (Utilidade) | 2200 / 2208 lb |
| CG Normal | dianteiro 35,0 in até 1950 lb → 41,0 in a 2550 lb; traseiro 47,3 in |
| CG Utilidade | dianteiro 35,0 in até 1950 lb → 37,5 in a 2200 lb; traseiro 40,5 in |
| Piloto/pax dianteiro | 37,0 in (trilho 34–46 in) |
| Passageiros traseiros | 73,0 in |
| Bagagem A / B | 95,0 in (máx. 120 lb) / 123,0 in (máx. 50 lb); A+B ≤ 120 lb |
| Combustível | 48,0 in; 53 gal utilizáveis; 6 lb/gal; táxi 1,1 gal |
| Utilidade | banco traseiro e bagageiro vazios |

## Estrutura

```
wb_calculator/
├── main.py              # ponto de entrada (CLI)
├── requirements.txt
├── wb/
│   ├── config.py        # AircraftSpec / StationSpec / CategorySpec + dados do C172S
│   ├── models.py        # LoadItem, LoadingCondition (burn_fuel, without_fuel)
│   ├── calculations.py  # ΣW, M = W·d, CG = ΣM/ΣW, tabela de momentos
│   ├── envelope.py      # polígono, check() estrito, check_path() da queima
│   ├── limits.py        # limites de estação, combinados, rampa, MTOW, categoria
│   ├── analysis.py      # orquestra Rampa → Decolagem → ZFW
│   ├── interface.py     # entrada interativa robusta
│   ├── report.py        # build_report() / export_report() → .txt
│   └── plotting.py      # gráfico Peso × CG
└── tests/test_wb.py     # 28 testes
```

## Configuração (terminal do VS Code)

```powershell
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
```bash
# Linux / macOS
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Execução

```bash
python main.py                                   # interativo (gera relatorios/wb_*.txt)
python main.py --demo                            # valores padrão
python main.py --demo --categoria utility
python main.py --relatorio saida/voo_0800.txt
python main.py --demo --sem-relatorio --no-show --save out/wb.png
python -m pytest -q
```

Códigos de saída: `0` aprovado · `1` não aprovado · `2` erro de dados · `130` cancelado.

## Política de validação da entrada

- **Bloqueado e pedido de novo:** texto, NaN/∞, negativos, braço fora do trilho
  do banco, combustível acima da capacidade. Após 5 tentativas inválidas, o
  programa usa o valor padrão. Vírgula decimal é aceita.
- **Aceito e reportado como violação:** valores fisicamente possíveis que excedem
  uma limitação (ex.: 90 lb na bagagem B). O piloto vê o problema no relatório.
- **Ctrl+C / Ctrl+D:** encerra limpo, sem traceback (código 130).

## Licença

Distribuído sob a licença MIT — veja [LICENSE](LICENSE).
