type MetricCardProps = {
  label: string;
  value: string | number;
  onClick?: () => void;
};

function MetricCard({
  label,
  value,
  onClick,
}: MetricCardProps) {
  return (
    <article
      className={onClick ? "card clickable-card" : "card"}
      onClick={onClick}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export default MetricCard;
