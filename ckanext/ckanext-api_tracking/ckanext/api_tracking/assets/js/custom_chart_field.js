document.addEventListener('DOMContentLoaded', function () {
    const data = window.trackingData;
    const trackingData = JSON.parse(data);
    console.log("Tracking Data=========>", trackingData);

    const ctx = document.getElementById('statisticsChart').getContext('2d');
    let chart; // Biến lưu trữ biểu đồ để có thể cập nhật lại

    // Hàm vẽ biểu đồ
    function renderChart(labels, activeCounts, publicCounts, privateCounts, chartType = 'bar') {
        if (chart) chart.destroy(); // Xóa biểu đồ cũ nếu đã tồn tại
        chart = new Chart(ctx, {
            type: chartType,
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'State Count',
                        data: activeCounts,
                        backgroundColor: 'rgba(153, 102, 255, 0.6)', // Màu tím
                        borderColor: 'rgba(153, 102, 255, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Public Count',
                        data: publicCounts,
                        backgroundColor: 'rgba(255, 206, 86, 0.6)', // Màu vàng
                        borderColor: 'rgba(255, 206, 86, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Private Count',
                        data: privateCounts,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)', // Màu đỏ
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Package States'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Count'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Hàm lấy dữ liệu và sắp xếp theo tiêu chí
    function prepareData(sortBy = 'asc', itemCount = 5) {
        const groupedData = {};

        trackingData.forEach(item => {
            const packageState = item.package_state;
            if (!groupedData[packageState]) {
                groupedData[packageState] = {
                    state_count: 0,
                    public_count: 0,
                    private_count: 0
                };
            }

            groupedData[packageState].state_count += item.state_count;
            groupedData[packageState].public_count += item.public_count;
            groupedData[packageState].private_count += item.private_count;
        });

        let sortedData = Object.entries(groupedData).map(([key, value]) => ({
            package_state: key,
            ...value
        }));

        if (sortBy === 'asc') {
            sortedData.sort((a, b) => a.state_count - b.state_count);
        } else if (sortBy === 'desc') {
            sortedData.sort((a, b) => b.state_count - a.state_count);
        }

        sortedData = sortedData.slice(0, itemCount);

        const labels = sortedData.map(item => item.package_state);
        const activeCounts = sortedData.map(item => item.state_count);
        const publicCounts = sortedData.map(item => item.public_count);
        const privateCounts = sortedData.map(item => item.private_count);

        renderChart(labels, activeCounts, publicCounts, privateCounts);
    }

    // Gọi hàm chuẩn bị dữ liệu và vẽ biểu đồ lần đầu
    prepareData();

    // Thêm sự kiện cho các phần tử chọn lọc
    document.getElementById('itemCount').addEventListener('input', function () {
        const itemCount = parseInt(this.value) || 5;
        const sortBy = document.getElementById('sortOptions').value;
        prepareData(sortBy, itemCount);
    });

    document.getElementById('sortOptions').addEventListener('change', function () {
        const sortBy = this.value;
        const itemCount = parseInt(document.getElementById('itemCount').value) || 5;
        prepareData(sortBy, itemCount);
    });

    document.getElementById('chartType').addEventListener('change', function () {
        const chartType = this.value;
        const sortBy = document.getElementById('sortOptions').value;
        const itemCount = parseInt(document.getElementById('itemCount').value) || 5;
        prepareData(sortBy, itemCount);
        chart.config.type = chartType;
        chart.update();
    });
});
