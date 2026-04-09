import ReactECharts from "echarts-for-react";
import type { ChartData, ChartSeries } from "../lib/api";

const palette = ["#19c2a7", "#2f80ed", "#41b6ff", "#f59e0b", "#ef476f", "#7c5cff"];

const localizationRules: Array<[RegExp, string]> = [
  [/\brevenue growth rate\b/gi, "营收增长率"],
  [/\brevenue\b/gi, "营收"],
  [/\bgross margin\b/gi, "毛利率"],
  [/\bnet margin\b/gi, "销售净利率"],
  [/\boperating margin\b/gi, "营业利润率"],
  [/\basset turnover\b/gi, "总资产周转率"],
  [/\bequity multiplier\b/gi, "权益乘数"],
  [/\binventory turnover\b/gi, "存货周转率"],
  [/\bdebt ratio\b/gi, "资产负债率"],
  [/\bcomparison\b/gi, "对比"],
  [/\btrend\b/gi, "趋势"],
  [/\bperiod\b/gi, "期间"],
  [/\bcompany\b/gi, "公司"],
  [/\bmetric\b/gi, "指标"],
  [/\bvisual brief\b/gi, "可视化简报"],
  [/\banalyst verdict\b/gi, "图表结论"],
  [/\bmax\b/gi, "最高"],
  [/\bmin\b/gi, "最低"],
  [/\baverage\b/gi, "均值"],
];

function formatNumber(value: number) {
  if (Number.isInteger(value)) {
    return `${value}`;
  }
  return value.toFixed(2).replace(/\.?0+$/, "");
}

function localizeText(text?: string) {
  if (!text) {
    return "";
  }

  let localized = `${text}`.trim();
  for (const [pattern, replacement] of localizationRules) {
    localized = localized.replace(pattern, replacement);
  }
  return localized;
}

function isTemporalAxis(labels: string[]) {
  if (labels.length < 2) {
    return false;
  }
  return labels.every((label) => /^(19|20)\d{2}$/.test(label));
}

function normalizeDatasets(chart: ChartData, xLabels: string[]) {
  const datasets = (chart.datasets ?? chart.series ?? []).filter(
    (dataset): dataset is ChartSeries =>
      Boolean(dataset) && Array.isArray(dataset.data) && dataset.data.length === xLabels.length,
  );

  return datasets.map((dataset) => ({
    name: localizeText(dataset.name || "系列"),
    data: dataset.data.map((value) => Number(value ?? 0)),
  }));
}

function buildComparisonVerdict(title: string, labels: string[], values: number[]) {
  const maxIndex = values.reduce((best, value, index, array) => (value > array[best] ? index : best), 0);
  const minIndex = values.reduce((best, value, index, array) => (value < array[best] ? index : best), 0);
  return `图中显示，${title}在${labels[maxIndex]}最高，为${formatNumber(values[maxIndex])}；在${labels[minIndex]}最低，为${formatNumber(values[minIndex])}。这说明不同对象之间存在明显差异。`;
}

function buildSingleTrendVerdict(title: string, labels: string[], values: number[]) {
  const start = values[0];
  const end = values[values.length - 1];
  const change = end - start;
  const trend = change > 0 ? "上升" : change < 0 ? "下降" : "基本持平";
  const implication = change > 0 ? "整体表现改善" : change < 0 ? "整体表现走弱" : "整体表现较为稳定";
  return `${labels[0]}至${labels[labels.length - 1]}年，${title}由${formatNumber(start)}${trend}至${formatNumber(end)}，${implication}。`;
}

function buildMultiSeriesTrendVerdict(
  title: string,
  labels: string[],
  datasets: Array<{ name: string; data: number[] }>,
) {
  const latestRanking = [...datasets]
    .map((dataset) => ({ name: dataset.name, value: dataset.data[dataset.data.length - 1] }))
    .sort((a, b) => b.value - a.value);
  const summary = datasets
    .map((dataset) => `${dataset.name}由${formatNumber(dataset.data[0])}变为${formatNumber(dataset.data[dataset.data.length - 1])}`)
    .join("；");

  const leader = latestRanking[0];
  const trailer = latestRanking[latestRanking.length - 1];
  return `${labels[0]}至${labels[labels.length - 1]}年，${title}方面，${summary}；${labels[labels.length - 1]}年${leader.name}最高，为${formatNumber(leader.value)}，${trailer.name}最低，为${formatNumber(trailer.value)}。`;
}

function normalizeChart(chart: ChartData) {
  const xLabels = (chart.x_labels ?? []).map((label) => localizeText(label));
  const temporal = isTemporalAxis(xLabels);
  const datasets = normalizeDatasets(chart, xLabels);
  const requestedType = (chart.chart_type ?? "bar").toLowerCase();
  const chartType = requestedType === "line" && !temporal ? "bar" : requestedType;
  const title = localizeText(chart.title ?? chart.chart_name ?? "图表");
  const strategicHighlight = localizeText(
    chart.strategic_highlight ?? (temporal ? `${xLabels[0]}-${xLabels[xLabels.length - 1]}` : "横向对比"),
  );

  let analystVerdict = localizeText(chart.analyst_verdict ?? "");
  if (!analystVerdict && datasets.length > 0) {
    if (temporal && datasets.length === 1) {
      analystVerdict = buildSingleTrendVerdict(title, xLabels, datasets[0].data);
    } else if (temporal) {
      analystVerdict = buildMultiSeriesTrendVerdict(title, xLabels, datasets);
    } else if (datasets.length === 1) {
      analystVerdict = buildComparisonVerdict(title, xLabels, datasets[0].data);
    }
  }

  return {
    title,
    chartType,
    xLabels,
    datasets,
    temporal,
    analystVerdict,
    strategicHighlight,
  };
}

function buildOption(chart: ChartData) {
  const normalized = normalizeChart(chart);
  const isPie = normalized.chartType === "pie" || normalized.chartType === "donut";
  const isDenseAxis =
    normalized.xLabels.length > 6 || normalized.xLabels.some((label) => label.length > 6);

  const series = normalized.datasets.map((dataset, index) => {
    const color = palette[index % palette.length];

    if (isPie) {
      return {
        name: dataset.name,
        type: "pie",
        radius: normalized.chartType === "donut" ? ["48%", "72%"] : "68%",
        data: dataset.data.map((value, valueIndex) => ({
          name: normalized.xLabels[valueIndex] ?? `项目${valueIndex + 1}`,
          value,
        })),
        itemStyle: {
          borderRadius: 10,
          borderColor: "#08131f",
          borderWidth: 2,
        },
        label: {
          show: true,
          color: "#e2e8f0",
          formatter: ({ name, value }: { name: string; value: number }) =>
            `${name}\n${formatNumber(value)}`,
        },
      };
    }

    if (normalized.chartType === "line") {
      return {
        name: dataset.name,
        type: "line",
        smooth: true,
        clip: false,
        data: dataset.data,
        symbolSize: 8,
        lineStyle: { width: 3, color },
        itemStyle: { color },
        label: {
          show: true,
          position: "top",
          color: "#dffcff",
          fontWeight: 700,
          formatter: ({ value }: { value: number }) => formatNumber(value),
        },
        markPoint: {
          symbolSize: 42,
          label: {
            color: "#08131f",
            fontWeight: 800,
            formatter: ({ data }: { data: { name: string; value: number } }) =>
              `${data.name}\n${formatNumber(data.value)}`,
          },
          data: [
            { type: "max", name: "最高" },
            { type: "min", name: "最低" },
          ],
        },
        markLine: {
          symbol: "none",
          lineStyle: {
            color: "rgba(125, 211, 252, 0.35)",
            type: "dashed",
          },
          label: {
            color: "#9ddceb",
            formatter: "均值",
          },
          data: [{ type: "average", name: "均值" }],
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${color}55` },
              { offset: 1, color: `${color}08` },
            ],
          },
        },
      };
    }

    return {
      name: dataset.name,
      type: "bar",
      clip: false,
      data: dataset.data,
      barMaxWidth: 38,
      itemStyle: {
        color,
        borderRadius: [10, 10, 0, 0],
      },
      label: {
        show: true,
        position: "top",
        color: "#dffcff",
        fontWeight: 700,
        formatter: ({ value }: { value: number }) => formatNumber(value),
      },
    };
  });

  return {
    backgroundColor: "transparent",
    color: palette,
    tooltip: {
      trigger: isPie ? "item" : "axis",
      backgroundColor: "rgba(8, 19, 31, 0.94)",
      borderColor: "rgba(125, 211, 252, 0.22)",
      textStyle: {
        color: "#e2e8f0",
      },
      formatter: (params: unknown) => {
        if (Array.isArray(params)) {
          const first = params[0] as { axisValueLabel?: string };
          const lines = params.map((item) => {
            const point = item as { seriesName?: string; value?: number; marker?: string };
            return `${point.marker ?? ""}${localizeText(point.seriesName)}: ${formatNumber(Number(point.value ?? 0))}`;
          });
          return [`${first?.axisValueLabel ?? ""}`, ...lines].join("<br/>");
        }

        const point = params as { name?: string; seriesName?: string; value?: number; marker?: string };
        return `${point.marker ?? ""}${point.name ?? localizeText(point.seriesName)}: ${formatNumber(Number(point.value ?? 0))}`;
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: "#94a3b8" },
    },
    grid: isPie
      ? undefined
      : {
          left: 24,
          right: 24,
          top: 42,
          bottom: isDenseAxis ? 88 : 68,
          containLabel: true,
        },
    xAxis: isPie
      ? undefined
      : {
          type: "category",
          data: normalized.xLabels,
          axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } },
          axisLabel: {
            color: "#94a3b8",
            interval: 0,
            rotate: isDenseAxis ? 28 : 0,
            hideOverlap: false,
          },
        },
    yAxis: isPie
      ? undefined
      : {
          type: "value",
          splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.08)" } },
          axisLabel: {
            color: "#94a3b8",
            formatter: (value: number) => formatNumber(value),
          },
        },
    dataZoom:
      !isPie && normalized.xLabels.length > 8
        ? [
            { type: "inside", zoomLock: false },
            {
              type: "slider",
              height: 12,
              bottom: 18,
              borderColor: "rgba(148, 163, 184, 0.12)",
              backgroundColor: "rgba(148, 163, 184, 0.08)",
              fillerColor: "rgba(25, 194, 167, 0.18)",
              handleStyle: {
                color: "#19c2a7",
              },
            },
          ]
        : undefined,
    series,
  };
}

interface EChartCardProps {
  chart: ChartData;
}

export function EChartCard({ chart }: EChartCardProps) {
  const normalized = normalizeChart(chart);

  return (
    <section className="chart-card">
      <div className="chart-card__header">
        <div>
          <span className="eyebrow">可视化简报</span>
          <h3>{normalized.title}</h3>
        </div>
        {normalized.strategicHighlight ? (
          <span className="chart-card__tag">{normalized.strategicHighlight}</span>
        ) : null}
      </div>
      <ReactECharts option={buildOption(chart)} style={{ height: 400 }} />
      {normalized.analystVerdict ? (
        <div className="chart-card__verdict">
          <span className="eyebrow">图表结论</span>
          <p>{normalized.analystVerdict}</p>
        </div>
      ) : null}
    </section>
  );
}
