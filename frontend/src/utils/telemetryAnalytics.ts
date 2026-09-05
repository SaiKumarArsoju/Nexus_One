import type { TelemetryAggregateBucket } from "../types/api";

export type ThresholdAnalytics = {
  exceedingBucketCount: number;
  exceedingBucketPercentage: number;
  readingsInExceedingBuckets: number;
  peakMaximum: number;
  peakBucketStart: string;
};

export function summarizeThresholdAnalytics(
  buckets: TelemetryAggregateBucket[],
  threshold: number,
): ThresholdAnalytics | null {
  if (buckets.length === 0) {
    return null;
  }

  const exceedingBuckets = buckets.filter(
    (bucket) => bucket.maximum > threshold,
  );
  const peakBucket = buckets.reduce((peak, bucket) => {
    if (bucket.maximum > peak.maximum) {
      return bucket;
    }

    if (
      bucket.maximum === peak.maximum &&
      Date.parse(bucket.bucket_start) < Date.parse(peak.bucket_start)
    ) {
      return bucket;
    }

    return peak;
  });

  return {
    exceedingBucketCount: exceedingBuckets.length,
    exceedingBucketPercentage:
      (exceedingBuckets.length / buckets.length) * 100,
    readingsInExceedingBuckets: exceedingBuckets.reduce(
      (total, bucket) => total + bucket.count,
      0,
    ),
    peakMaximum: peakBucket.maximum,
    peakBucketStart: peakBucket.bucket_start,
  };
}

export function calculateTelemetryYAxisDomain(
  buckets: TelemetryAggregateBucket[],
  threshold?: number,
): [number | "auto", number | "auto"] {
  const values = buckets
    .flatMap((bucket) => [bucket.minimum, bucket.maximum])
    .filter(Number.isFinite);

  if (threshold !== undefined && Number.isFinite(threshold)) {
    values.push(threshold);
  }

  if (values.length === 0) {
    return ["auto", "auto"];
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = maximum - minimum;
  const magnitude = Math.max(Math.abs(minimum), Math.abs(maximum), 1);
  const padding = Math.max(spread * 0.1, magnitude * 0.01);

  return [minimum - padding, maximum + padding];
}
