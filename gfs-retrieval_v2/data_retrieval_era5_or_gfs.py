import cdsapi

c = cdsapi.Client()

c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': ['2m_temperature', 'total_precipitation'],
        'year': '2023',
        'month': '06',
        'day': ['01', '02'],
        'time': ['00:00', '06:00', '12:00', '18:00'],
        'format': 'netcdf',
    },
    'era5_data.nc'
)
