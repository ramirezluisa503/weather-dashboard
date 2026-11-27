import { useState } from 'react';
import { Alert, Button, Input, Table } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { getExportUrl } from '../api/weatherApi';
import useWeatherHistory from '../hooks/useWeatherHistory';

const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

const COLUMNS = [
  { title: 'Ciudad', dataIndex: 'city', key: 'city' },
  {
    title: 'Temperatura',
    dataIndex: 'temperature',
    key: 'temperature',
    align: 'right',
    render: (value) => `${value.toFixed(1)} °C`,
  },
  {
    title: 'Humedad',
    dataIndex: 'humidity',
    key: 'humidity',
    align: 'right',
    render: (value) => `${value} %`,
  },
  {
    title: 'Viento',
    dataIndex: 'wind_speed',
    key: 'wind_speed',
    align: 'right',
    render: (value) => `${value.toFixed(1)} m/s`,
  },
  {
    title: 'Medición',
    dataIndex: 'timestamp',
    key: 'timestamp',
    render: (value) => dateFormatter.format(new Date(value)),
  },
];

export default function HistoryTable() {
  const [city, setCity] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const { rows, total, error, loading } = useWeatherHistory({
    city,
    page,
    pageSize,
  });

  const handleSearch = (value) => {
    setCity(value.trim());
    setPage(1);
  };

  const handleTableChange = (pagination) => {
    if (pagination.pageSize !== pageSize) {
      setPageSize(pagination.pageSize);
      setPage(1);
    } else {
      setPage(pagination.current);
    }
  };

  return (
    <section className="history-card glass glass--solid">
      <header className="history-card__header">
        <h2>Histórico de mediciones</h2>
        <div className="history-card__actions">
          <Input.Search
            placeholder="Filtrar por ciudad"
            allowClear
            maxLength={100}
            onSearch={handleSearch}
            aria-label="Filtrar por ciudad"
          />
          <Button
            icon={<DownloadOutlined />}
            href={getExportUrl(city)}
          >
            Exportar CSV
          </Button>
        </div>
      </header>

      {error && (
        <Alert
          type="error"
          showIcon
          title="No se pudo cargar el histórico"
          description={error}
        />
      )}

      <Table
        rowKey="id"
        columns={COLUMNS}
        dataSource={rows}
        loading={loading}
        size="middle"
        scroll={{ x: 640 }}
        onChange={handleTableChange}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50],
          showTotal: (count) => `${count} registros`,
        }}
      />
    </section>
  );
}
