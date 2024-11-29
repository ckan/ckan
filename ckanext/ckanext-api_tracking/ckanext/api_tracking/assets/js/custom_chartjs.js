document.addEventListener("DOMContentLoaded", function () {
  const data = window.trackingData;
  const trackingData = JSON.parse(data);

  const itemCountInput = document.getElementById('itemCount');
  const sortOptions = document.getElementById('sortOptions');
  const chartTypeSelect = document.getElementById('chartType'); // Phần tử select cho kiểu biểu đồ
  const ctx = document.getElementById('trackingChart').getContext('2d');
  const resourceChartCtx = document.getElementById('resourceChart').getContext('2d');

  let packageChartInstance = null;
  let resourceChartInstance = null;

  // Sorting function for both package and resource data
  function sortData(data, option, isResource = false) {
    if (isResource) {
      // Sorting resource data
      switch (option) {
        case 'asc':
          return data.sort((a, b) => a.resource_view - b.resource_view); // Sort by resource views ascending
        case 'desc':
          return data.sort((a, b) => b.resource_view - a.resource_view); // Sort by resource views descending
        case 'nameAsc':
          return data.sort((a, b) => a.resource_name.localeCompare(b.resource_name)); // Sort by resource name A-Z
        case 'nameDesc':
          return data.sort((a, b) => b.resource_name.localeCompare(a.resource_name)); // Sort by resource name Z-A
        default:
          return data;
      }
    } else {
      // Sorting package data
      switch (option) {
        case 'asc':
          return data.sort((a, b) => a.package_view - b.package_view); // Sort by package views ascending
        case 'desc':
          return data.sort((a, b) => b.package_view - a.package_view); // Sort by package views descending
        case 'nameAsc':
          return data.sort((a, b) => a.title.localeCompare(b.title)); // Sort by package name A-Z
        case 'nameDesc':
          return data.sort((a, b) => b.title.localeCompare(a.title)); // Sort by package name Z-A
        default:
          return data;
      }
    }
  }

  // Create Package Chart
  function createPackageChart(displayData) {
    const labels = displayData.map(pkg => pkg.title);
    const viewsData = displayData.map(pkg => pkg.package_view);
    const downloadData = displayData.map(pkg => pkg.package_download);

    if (packageChartInstance) {
      packageChartInstance.destroy();
    }

    // Get the selected chart type from the dropdown
    const chartType = chartTypeSelect.value;

    packageChartInstance = new Chart(ctx, {
      type: chartType,  // Use the selected chart type
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Package Views',
            data: viewsData,
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
          },
          {
            label: 'Package Downloads',
            data: downloadData,
            backgroundColor: 'rgba(153, 102, 255, 0.2)',
            borderColor: 'rgba(153, 102, 255, 1)',
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true
          }
        }
      }
    });
  }

  // Hàm gộp tài nguyên trùng tên
  function mergeResources(resources) {
    const mergedResources = {};

    resources.forEach(res => {
      if (mergedResources[res.resource_name]) {
        // Nếu tài nguyên đã tồn tại, cộng dồn views và downloads
        mergedResources[res.resource_name].resource_view += res.resource_view;
        mergedResources[res.resource_name].download_count += res.download_count;
      } else {
        // Nếu tài nguyên chưa tồn tại, thêm vào
        mergedResources[res.resource_name] = { 
          resource_name: res.resource_name,
          resource_view: res.resource_view,
          download_count: res.download_count
        };
      }
    });

    // Chuyển đối tượng mergedResources thành một mảng để vẽ biểu đồ
    return Object.values(mergedResources);
  }

  // Show Resource Chart
  function showResourceChart(resources) {
    const count = parseInt(itemCountInput.value, 10) || 5;
    const sortOption = sortOptions.value; // Get the selected sort option
    let sortedResources = [...resources]; // Make a copy to avoid mutation
    sortedResources = sortData(sortedResources, sortOption, true); // Sort resources based on selected option

    // Gộp các tài nguyên có cùng tên
    const mergedResources = mergeResources(sortedResources);

    const limitedResources = mergedResources.slice(0, count);

    if (limitedResources.length > 0) {
      const resourceLabels = limitedResources.map(res => res.resource_name);
      const downloadData = limitedResources.map(res => res.download_count);
      const viewsData = limitedResources.map(res => res.resource_view);

      if (resourceChartInstance) {
        resourceChartInstance.destroy();
      }

      const chartType = chartTypeSelect.value;  // Get the selected chart type for resource chart

      resourceChartInstance = new Chart(resourceChartCtx, {
        type: chartType,  // Use the selected chart type
        data: {
          labels: resourceLabels,
          datasets: [
            {
              label: 'Resource Downloads',
              data: downloadData,
              backgroundColor: 'rgba(153, 102, 255, 0.2)',
              borderColor: 'rgba(153, 102, 255, 1)',
              borderWidth: 1
            },
            {
              label: 'Resource Views',
              data: viewsData,
              backgroundColor: 'rgba(255, 159, 64, 0.2)',
              borderColor: 'rgba(255, 159, 64, 1)',
              borderWidth: 1
            }
          ]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      });

      document.getElementById('title_resource').style.display = 'block';
      document.getElementById('resourceChartContainer').style.display = 'block'
      document.getElementById('noResourceMessage').style.display = 'none'; // Ẩn thông báo khi có dữ liệu;
    } else {
      hideResourceChart();
      document.getElementById('noResourceMessage').style.display = 'block'; // Ẩn thông báo khi có dữ liệu
    }
  }

  // Hide Resource Chart
  function hideResourceChart() {
    document.getElementById('title_resource').style.display = 'none';
    document.getElementById('resourceChartContainer').style.display = 'none';
    document.getElementById('noResourceMessage').style.display = 'none'; // Ẩn thông báo khi có dữ liệu
  }

  // Update charts based on input count and sort option
  function updateCharts() {
    const count = parseInt(itemCountInput.value, 10) || 5;
    const sortOption = sortOptions.value;

    // Sort the package data based on the selected option
    let sortedData = [...trackingData]; // Make a copy of the trackingData
    sortedData = sortData(sortedData, sortOption); // Sort package data

    // Limit the data to the selected count
    const limitedData = sortedData.slice(0, count);

    // Create package chart
    createPackageChart(limitedData);

    // Hide resource chart initially
    hideResourceChart();

    // Show the resource chart for the first package if clicked
    ctx.canvas.addEventListener('click', function (e) {
      const activePoints = packageChartInstance.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
      if (activePoints.length > 0) {
        const dataIndex = activePoints[0].index;
        const resources = limitedData[dataIndex].include_resources;
        showResourceChart(resources);  // Update resource chart after sorting and merging
      } else {
        hideResourceChart();
        document.getElementById('noResourceMessage').style.display = 'block'; // Ẩn thông báo khi có dữ liệu
      }
    });
  }

  // Listen to the sort option change and update charts accordingly
  sortOptions.addEventListener('change', updateCharts);

  // Listen to the item count input change and update charts accordingly
  itemCountInput.addEventListener('input', updateCharts);

  // Listen to the chart type change and update charts accordingly
  chartTypeSelect.addEventListener('change', updateCharts);

  // Initial update
  updateCharts();
});
