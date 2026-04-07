import ReactECharts from "echarts-for-react";
import type { ChartData } from "../lib/api";

const palette = ["#5eead4", "#7dd3fc", "#38bdf8", "#f59e0b", "#fb7185", "#a78bfa"];

function buildOption(chart: ChartData) {
  const chartType = chart.chart_type ?? "bar";
  const datasets = chart.datasets ?? chart.series ?? [];
  const xLabels = chart.x_labels ?? [];
  const isPie = chartType === "pie" || chartType === "donut";

  const series = datasets.map((dataset, index) => {
    const color = palette[index % palette.length];
    if (isPie) {
      return {
        name: dataset.name,
        type: "pie",
        radius: chartType === "donut" ? ["48%", "72%"] : "68%",
        data: dataset.data.map((value, valueIndex) => ({
          name: xLabels[valueIndex] ?? `Item ${valueIndex + 1}`,
          value,
        })),
        itemStyle: {
          borderRadius: 10,
          borderColor: "#07111c",
          borderWidth: 2,
        },
      };
    }

    if (chartType === "line") {
      return {
        name: dataset.name,
        type: "line",
        smooth: true,
        data: dataset.data,
        symbolSize: 8,
        lineStyle: { width: 3, color },
        itemStyle: { color },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: `${color}66` },
              { offset: 1, color: `${color}05` },
            ],
          },
        },
      };
    }

    return {
      name: dataset.name,
      type: "bar",
      data: dataset.data,
      barMaxWidth: 34,
      itemStyle: {
        color,
        borderRadius: [10, 10, 0, 0],
      },
    };
  });

  return {
    backgroundColor: "transparent",
    color: palette,
    tooltip: {
      trigger: isPie ? "item" : "axis",
      backgroundColor: "rgba(7, 17, 28, 0.92)",
      borderColor: "rgba(125, 211, 252, 0.22)",
      textStyle: {
        color: "#e2e8f0",
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
          right: 20,
          top: 52,
          bottom: 56,
          containLabel: true,
        },
    title: {
      text: chart.title ?? chart.chart_name ?? "智能图表",
      left: 20,
      top: 18,
      textStyle: {
        color: "#f8fafc",
        fontSize: 16,
        fontWeight: 700,
      },
    },
    xAxis: isPie
      ? undefined
      : {
          type: "category",
          data: xLabels,
          axisLine: { lineStyle: { color: "rgba(148, 163, 184, 0.2)" } },
          axisLabel: { color: "#94a3b8" },
        },
    yAxis: isPie
      ? undefined
      : {
          type: "value",
          splitLine: { lineStyle: { color: "rgba(148, 163, 184, 0.08)" } },
          axisLabel: { color: "#94a3b8" },
        },
    series,
  };
}

interface EChartCardProps {
  chart: ChartData;
}

export function EChartCard({ chart }: EChartCardProps) {
  return (
    <section className="chart-card">
      <div className="chart-card__header">
        <div>
          <span className="eyebrow">Visual Brief</span>
          <h3>{chart.title ?? chart.chart_name ?? "智能图表"}</h3>
        </div>
        {chart.strategic_highlight ? (
          <span className="chart-card__tag">{chart.strategic_highlight}</span>
        ) : null}
      </div>
      <ReactECharts option={buildOption(chart)} style={{ height: 360 }} />
      {chart.analyst_verdict ? (
        <div className="chart-card__verdict">
          <span className="eyebrow">Analyst Verdict</span>
          <p>{chart.analyst_verdict}</p>
        </div>
      ) : null}
    </section>
  );
}
