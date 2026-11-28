import { useState } from 'react';
import { AutoComplete, Button } from 'antd';
import { SearchOutlined, SwapOutlined } from '@ant-design/icons';

const SUGGESTED_CITIES = [
  'Bogota',
  'Medellin',
  'Cali',
  'Barranquilla',
  'Cartagena',
  'Bucaramanga',
  'Pereira',
  'Manizales',
  'Santa Marta',
  'Leticia',
  'Madrid',
  'Lima',
  'Buenos Aires',
  'London',
  'Tokyo',
  'New York',
];
const CITY_OPTIONS = SUGGESTED_CITIES.map((city) => ({ value: city }));

const filterCity = (input, option) =>
  option.value.toLowerCase().includes(input.toLowerCase());

export default function CitySelector({
  initialCity1,
  initialCity2,
  loading,
  onCompare,
}) {
  const [city1, setCity1] = useState(initialCity1);
  const [city2, setCity2] = useState(initialCity2);
  const [error, setError] = useState(null);

  const handleSubmit = (event) => {
    event.preventDefault();
    const first = city1.trim();
    const second = city2.trim();

    if (!first || !second) {
      setError('Escribe las dos ciudades.');
      return;
    }
    if (first.toLowerCase() === second.toLowerCase()) {
      setError('Elige dos ciudades diferentes.');
      return;
    }
    setError(null);
    onCompare(first, second);
  };

  const handleSwap = () => {
    setCity1(city2);
    setCity2(city1);
  };

  return (
    <form
      className="city-selector panel"
      onSubmit={handleSubmit}
    >
      <AutoComplete
        className="city-selector__input"
        value={city1}
        onChange={setCity1}
        options={CITY_OPTIONS}
        filterOption={filterCity}
        placeholder="Primera ciudad"
        aria-label="Primera ciudad"
        maxLength={100}
      />
      <Button
        shape="circle"
        icon={<SwapOutlined />}
        onClick={handleSwap}
        aria-label="Intercambiar ciudades"
      />
      <AutoComplete
        className="city-selector__input"
        value={city2}
        onChange={setCity2}
        options={CITY_OPTIONS}
        filterOption={filterCity}
        placeholder="Segunda ciudad"
        aria-label="Segunda ciudad"
        maxLength={100}
      />
      <Button
        type="primary"
        htmlType="submit"
        icon={<SearchOutlined />}
        loading={loading}
      >
        Comparar
      </Button>
      {error && <p className="city-selector__error">{error}</p>}
    </form>
  );
}
