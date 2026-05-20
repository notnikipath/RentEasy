import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const gatewayUrl = (import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:32059").replace(/\/+$/, "");

const emptyDashboard = {
  host_id: "HOST-001",
  listings: { items: [], count: 0 },
  bookings: { items: [], count: 0 },
  owner_analytics: {
    revenue: 0,
    expenses: 0,
    occupancy_rate: 0,
    profit: 0,
    margin_pct: 0,
    profit_per_listing: 0,
  },
  reviews: { items: [], count: 0, avg_rating: 0 },
  notifications: { items: [], count: 0 },
  kpi: {
    search_latency_p95_ms: 0,
    booking_latency_p95_ms: 0,
    search_time_target_sec: 2,
    booking_time_target_sec: 5,
    listing_capacity_target: 1000000,
    search_target_met: true,
    booking_target_met: true,
    status_breakdown: {},
  },
};

async function loadDashboard(hostId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${hostId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [hostId, setHostId] = useState("HOST-001");
  const [theme, setTheme] = useState("light");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyDashboard);

  useEffect(() => {
    let active = true;

    loadDashboard(hostId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDashboard({ ...emptyDashboard, ...payload });
        setStatus("succeeded");
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setStatus("failed");
        setError(err.message);
      });

    return () => {
      active = false;
    };
  }, [hostId]);

  const listingItems = dashboard.listings?.items || [];
  const bookingItems = dashboard.bookings?.items || [];
  const reviewItems = dashboard.reviews?.items || [];
  const notificationItems = dashboard.notifications?.items || [];

  const statusLabel = useMemo(() => {
    if (status === "loading") {
      return "loading";
    }
    if (status === "failed") {
      return "fallback";
    }
    return "live";
  }, [status]);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(hostId);
      setDashboard({ ...emptyDashboard, ...payload });
      setStatus("succeeded");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  return (
    <div className={`app theme-${theme}`}>
      <div className="background-orb orb-a" />
      <div className="background-orb orb-b" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">RentEasy Platform</p>
          <h1>Аренда жилья и коммерческой недвижимости в единой микросервисной платформе.</h1>
          <p className="sub">
            Объявления, поиск, онлайн-бронирование, безопасные платежи, коммуникация и аналитика владельцев.
          </p>
          <div className="hero-badges">
            <span>Search under 2 sec</span>
            <span>Booking under 5 sec</span>
            <span>1M listings capacity</span>
            <span>Saved searches and recommendations</span>
          </div>
        </div>

        <div className="hero-panel">
          <label>
            Host ID
            <input value={hostId} onChange={(event) => setHostId(event.target.value)} placeholder="HOST-001" />
          </label>
          <div className="hero-actions">
            <button onClick={refresh}>Refresh dashboard</button>
            <button className="ghost" onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}>
              Theme
            </button>
          </div>
          <p className="status-line">Status: {statusLabel}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          title="Search P95"
          value={`${Number(dashboard.kpi?.search_latency_p95_ms || 0).toFixed(0)} ms`}
          target={`Target < ${(dashboard.kpi?.search_time_target_sec || 2).toFixed(1)} sec`}
          ok={Boolean(dashboard.kpi?.search_target_met)}
        />
        <KpiCard
          title="Booking P95"
          value={`${Number(dashboard.kpi?.booking_latency_p95_ms || 0).toFixed(0)} ms`}
          target={`Target < ${(dashboard.kpi?.booking_time_target_sec || 5).toFixed(1)} sec`}
          ok={Boolean(dashboard.kpi?.booking_target_met)}
        />
        <KpiCard
          title="Occupancy"
          value={`${Math.round((dashboard.owner_analytics?.occupancy_rate || 0) * 100)}%`}
          target="Target > 70%"
          ok={Number(dashboard.owner_analytics?.occupancy_rate || 0) >= 0.7}
        />
        <KpiCard
          title="Profit"
          value={`${Math.round(dashboard.owner_analytics?.profit || 0).toLocaleString()} RUB`}
          target="Positive margin"
          ok={Number(dashboard.owner_analytics?.profit || 0) > 0}
        />
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="content-grid">
        <article className="panel panel-featured">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Owner Snapshot</p>
              <h2>{dashboard.host_id}</h2>
            </div>
            <span className="pill">{listingItems.length} listings</span>
          </div>
          <p className="panel-copy">
            Dashboard показывает текущую загрузку объектов, подтвержденные бронирования, средний рейтинг и историю уведомлений.
          </p>
          <div className="metrics-row">
            <div>
              <strong>{bookingItems.length}</strong>
              <span>bookings</span>
            </div>
            <div>
              <strong>{reviewItems.length}</strong>
              <span>reviews</span>
            </div>
            <div>
              <strong>{Number(dashboard.reviews?.avg_rating || 0).toFixed(1)}</strong>
              <span>avg rating</span>
            </div>
            <div>
              <strong>{dashboard.kpi?.listing_capacity_target || 1000000}</strong>
              <span>target listings</span>
            </div>
          </div>
          <TaskBoard bookings={bookingItems} />
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Listings</p>
              <h2>Активные объекты</h2>
            </div>
            <span className="pill accent">{listingItems.length}</span>
          </div>
          <div className="stack-list">
            {listingItems.map((listing) => (
              <div className="stack-item" key={listing.listing_id}>
                <div>
                  <p className="stack-title">{listing.title}</p>
                  <p className="stack-sub">
                    {listing.geo.city}, {listing.geo.district} · {listing.area_m2} m2
                  </p>
                </div>
                <span>{Math.round(listing.pricing.monthly_price).toLocaleString()} RUB</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Profitability</p>
              <h2>Доходность владельца</h2>
            </div>
            <span className="pill">{Number(dashboard.owner_analytics?.margin_pct || 0).toFixed(1)}%</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{Math.round(dashboard.owner_analytics?.revenue || 0).toLocaleString()}</strong>
              <span>revenue</span>
            </div>
            <div>
              <strong>{Math.round(dashboard.owner_analytics?.expenses || 0).toLocaleString()}</strong>
              <span>expenses</span>
            </div>
            <div>
              <strong>{Math.round(dashboard.owner_analytics?.profit || 0).toLocaleString()}</strong>
              <span>profit</span>
            </div>
            <div>
              <strong>{Math.round(dashboard.owner_analytics?.profit_per_listing || 0).toLocaleString()}</strong>
              <span>profit/listing</span>
            </div>
          </div>
        </article>

        <article className="panel panel-analytics">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Notifications</p>
              <h2>Последние уведомления платформы</h2>
            </div>
            <span className="pill accent">{notificationItems.length}</span>
          </div>
          <div className="timeline-list">
            {notificationItems.slice(-5).reverse().map((item, index) => (
              <div className="stack-item" key={`${item.subject}-${index}`}>
                <div>
                  <p className="stack-title">{item.subject}</p>
                  <p className="stack-sub">{item.body}</p>
                </div>
                <span>{item.channel}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
