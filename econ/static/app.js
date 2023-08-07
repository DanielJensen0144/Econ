// add sliding animations yay
const observer = new IntersectionObserver((elements) => {
  elements.forEach((el) => {
    if (el.isIntersecting) {
      el.target.classList.add("show");
    }
  });
});

const hidden = document.querySelectorAll(".hidden")
hidden.forEach((el) => observer.observe(el));


// add the graphing function
let myChart;
makeGraph();


// Elements for dark mode
let darkSwitch = document.getElementById("darkModeBtn");
if (darkSwitch == null) {
  darkSwitch = document.getElementById("darkmodeBtn");
}
let elements = {
  darkSwitch: document.getElementById("darkModeBtn"),
  darkBody: document.querySelector("body"),
  darkTxt: document.querySelectorAll(".darkTxt"),
  darkTable: document.querySelector("table"),
  darkLogoLight: document.getElementById("logo-light"),
  darkLogoDark: document.getElementById("logo-dark"),
  darkNav: document.querySelector("nav"),
  darkLine: document.getElementById("lineColor"),
  darkNode: document.getElementById("nodeColor"),
  darkScales: document.getElementById("scalesColor"),
  darkCard: document.querySelectorAll(".card")
  };
if (elements["darkSwitch"] == null) {
  elements["darkSwitch"] = document.getElementById("darkmodeBtn");
}
  
  // store dark mode state in local storage
  function setDarkModeLocalStorage(isDarkMode) {
    localStorage.setItem('darkMode', isDarkMode);
  }
  
  function getDarkModeFromLocalStorage() {
    const storedValue = localStorage.getItem("darkMode");
    return storedValue === 'true';
}

// Function to save dark mode state in a cookie
function setDarkModeCookie(isDarkMode) {
  document.cookie = `darkMode=${isDarkMode}; path=/`;
}

// Function to read dark mode state from a cookie
function getDarkModeFromCookie() {
  const cookieValue = document.cookie
  .split('; ')
  .find(row => row.startsWith("darkMode="))
  ?.split('=')[1];
  
  return cookieValue === 'true';
}


// Function to apply dark mode styles
function applyDarkMode(isDarkMode) {
  const { darkBody, darkTxt, darkTable, darkLogoLight, darkLogoDark, darkNav, darkLine, darkNode, darkScales, darkCard } = elements;
  if (isDarkMode) {
    // dim everything down
    darkBody.classList.add('backgroundDark');
    darkTxt.forEach((element) => element.classList.add('txtDark'));
    darkNav.setAttribute("data-bs-theme", "dark");
    if (darkTable) {
      darkTable.classList.add('table-dark');
    }
    if (darkLine && darkNode && darkScales) {
      darkLine.innerHTML = '#fff';
      darkNode.innerHTML = '#212529';
      darkScales.innerHTML = '#fff';
      makeGraph();
    }
    
    // change logo smoothly
    darkLogoLight.style.display = "none";
    darkLogoLight.style.opacity = 0;
    darkLogoDark.style.display = "block";
    darkLogoDark.style.opacity = 1;

    if (darkCard) {
      darkCard.forEach((el) => {
        el.classList.add('text-bg-dark');
        el.classList.remove('border-dark');
        el.classList.add('border-light');
      })
    }
    
    // change the local storage and cookie status
    setDarkModeLocalStorage(isDarkMode);
    setDarkModeCookie(isDarkMode);
  } else {
      // lighten everything up
      darkBody.classList.remove('backgroundDark');
      darkTxt.forEach((element) => element.classList.remove('txtDark'));
      darkNav.setAttribute("data-bs-theme", "light");
      if (darkTable) {
        darkTable.classList.remove('table-dark');
      }
      
      // change logo back smoothly
      darkLogoLight.style.display = "block";
      darkLogoLight.style.opacity = 1;
      darkLogoDark.style.display = "none";
      darkLogoDark.style.opacity = 0;
      
      if (darkCard) {
        darkCard.forEach((el) => {
          el.classList.remove('text-bg-dark');
          el.classList.remove('border-light');
          el.classList.add('border-dark');
        })
      }

      // change the local storage and cookie status
      setDarkModeLocalStorage(isDarkMode);
      setDarkModeCookie(isDarkMode);

      // change the graph colors back
      if (darkLine && darkNode && darkScales) {
        darkLine.innerHTML = '#0d6efd';
        darkNode.innerHTML = '#fff';
        darkScales.innerHTML = '#212529';
        makeGraph();
      }
    }
  }  
  
// Read dark mode state from a cookie after the page loads
const isDarkModeLocalStorage = getDarkModeFromLocalStorage();
const isDarkModeCookie = getDarkModeFromCookie();
const isDarkMode = isDarkModeLocalStorage !== null ? isDarkModeLocalStorage : isDarkModeCookie;
darkSwitch.checked = isDarkMode;

// Event listener to toggle dark mode on switch change
darkSwitch.addEventListener('change', function() {
  const isDarkMode = darkSwitch.checked;
  applyDarkMode(isDarkMode);
});
applyDarkMode(isDarkMode);
  
  
// graphing 
function makeGraph() {
  if (document.getElementById("documentName") && document.getElementById("documentName").innerHTML == 'research') {
    dataAdjustedClose = document.querySelectorAll(".dataAdjustedClose");
    dataDate = document.querySelectorAll(".dataDate");
  
    adjustedCloseData = [];
    dateLabels = [];
  
  
    dataAdjustedClose.forEach((el) => {
      adjustedCloseData.push(parseFloat(el.innerHTML));
    });
  
    dataDate.forEach((el) => {
      dateLabels.push(el.innerHTML);
    });
  
  
  
    days = document.getElementById("dayCount").innerHTML;
  
    adjustedCloseData.reverse();
    dateLabels.reverse();
  
    lineColor = document.getElementById("lineColor").innerHTML;
    nodeColor = document.getElementById("nodeColor").innerHTML;
    scalesColor = document.getElementById("scalesColor").innerHTML;

    let data = {
      labels: dateLabels,
      datasets: [
          {
            label: 'Adjusted Close',
            data: adjustedCloseData,
            borderColor: lineColor,
            backgroundColor: nodeColor,
            borderWidth: 3
          }
      ],
    };

    if (days > 99 && days < 241) {
      data = {
        labels: dateLabels,
        datasets: [
            {
              label: 'Adjusted Close',
              data: adjustedCloseData,
              borderColor: lineColor,
              backgroundColor: nodeColor,
              borderWidth: 3,
              fill: false,
              pointRadius: adjustedCloseData.map((value, i) => i % 4 === 0 || i === adjustedCloseData.length - 1 ? 3 : 0)
            }
        ],
      };
    }

    if (days > 241) {
      data = {
        labels: dateLabels,
        datasets: [
            {
              label: 'Adjusted Close',
              data: adjustedCloseData,
              borderColor: lineColor,
              backgroundColor: nodeColor,
              borderWidth: 2,
              fill: false,
              pointRadius: adjustedCloseData.map((value, i) => i % 8 === 0 || i === adjustedCloseData.length - 1 ? 3 : 0)
            }
        ],
      };
    }

  
    if (myChart) {
      myChart.destroy();
    }
  
    const options = {
      scales: {
        x: {
          ticks: {
            color: scalesColor
          }
        },
        y: {
          ticks: {
            color: scalesColor
          }
        }
      },
      plugins: {
        legend: {
          labels: {
            color: scalesColor
          }
        }
      }
    }
  
    const ctx = document.getElementById("myChart").getContext("2d");
    myChart = new Chart(ctx, {
      type: 'line',
      data: data,
      options: options
    });
  
    console.log("DANIEL IS SO COOL");
  }
  }

  // make graph
  makeGraph();