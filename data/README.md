# Safe Harbor Index — Data Pipeline

Updates the map with real data from public APIs.

## Quick Start

```bash
cd safe-map/data
pip install requests
python update.py
```

This fetches fresh data from World Bank and updates `index.html`.

## With Numbeo (better cost/safety/health data)

1. Get a free API key at https://www.numbeo.com/common/register.jsp
2. Run:
```bash
python update.py --numbeo-key YOUR_KEY
```

## Options

```
--refresh        Force re-fetch from APIs (ignores 7-day cache)
--numbeo-key     Numbeo API key for cost/safety/healthcare data
--dry-run        Print generated JS without writing to index.html
```

## Data Sources

| Parameter | Source | Notes |
|---|---|---|
| stability | World Bank PV.EST + RL.EST + CC.EST | Avg of 3 governance indicators |
| economy | World Bank NY.GDP.PCAP.CD | Log scale |
| employment | World Bank SL.UEM.TOTL.ZS | Inverted unemployment rate |
| density | World Bank EN.POP.DNST | Log scale, inverted |
| food | World Bank AG.PRD.FOOD.XD | Food Production Index |
| tech | World Bank IT.NET.USER.ZS | Internet penetration % |
| health | Numbeo Healthcare Index / World Bank SP.DYN.LE00.IN | Numbeo preferred |
| safety | Numbeo Safety Index / World Bank VC.IHR.PSRC.P5 | Numbeo preferred |
| cost | Numbeo Cost of Living Index | Inverted |
| military | World Bank MS.MIL.XPND.GD.ZS | % GDP proxy only |
| nuclear | **manual_data.json** | Cannot be automated |
| geography | **manual_data.json** | Distance from ME conflict |
| neighbors | **manual_data.json** | Neighbor stability |
| immigration | **manual_data.json** | Visa/residency access |
| resource | **manual_data.json** | Energy self-sufficiency |
| climate | **manual_data.json** | Long-term habitability |
| crypto | **manual_data.json** | Legal/regulatory status |
| taxes | **manual_data.json** | Tax burden |
| business | **manual_data.json** | Ease of doing business |
| terrorism | **manual_data.json** | Set from GPI CSV manually |

## Adding Global Peace Index (terrorism data)

1. Download GPI data from https://www.visionofhumanity.org/maps/
2. Export as CSV
3. Add a `terrorism` field to each entry in `manual_data.json`
   (invert GPI score: lower GPI rank = higher terrorism score)

## Cache

Fetched data is cached in `cache/` for 7 days. Delete cache files to force refresh.
