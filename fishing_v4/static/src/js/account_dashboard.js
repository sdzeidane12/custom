odoo.define('fishingDashboard.fishingDashboard', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var currency;
    var ActionMenu = AbstractAction.extend({

        contentTemplate: 'fishingDashboard',

        renderElement: function (ev) {
            var self = this;
            $.when(this._super())
                .then(function (ev) {
                    let product_id = 0
                    let tunnel_id = 0

                    //loading data for the fist time
                    rpc.query({
                        model: "fishing.reception.detail",
                        method: 'search_read',
                        args: [[['status', '!=', '6']], []],
                    })
                        .then(function (result) {
                            console.log(result)
                            // Statistics data

                            //reception
                            var reception_prod = 0
                            var reception_serv = 0

                            //treatment
                            var treatment_prod = 0
                            var treatment_serv = 0

                            //tunnel
                            var tunnel_prod = 0
                            var tunnel_serv = 0

                            //pkging
                            var packaging_prod = 0
                            var packaging_serv = 0

                            //   Quality indicator data
                            var qualities = [];
                            var quality_data = [];

                            var products = [];
                            var tunnels = [];


                            result.map(r => {
                                switch (r.status) {
                                    case '0':
                                        r.type == 'service' ? reception_serv += r.qte : reception_prod += r.qte
                                        break
                                    case '1':
                                        r.type == 'service' ? treatment_serv += r.qte : treatment_prod += r.qte
                                        break
                                    case '3':
                                        r.type == 'service' ? tunnel_serv += r.qte : tunnel_prod += r.qte
                                        break
                                    case '5':
                                        r.type == 'service' ? packaging_serv += r.qte : packaging_prod += r.qte
                                        break
                                }
                                if (qualities.includes(r.quality[1])) {
                                    let qindex = qualities.indexOf(r.quality[1])
                                    quality_data[qindex] += r.qte
                                } else {
                                    qualities.push(r.quality[1]);
                                    quality_data.push(r.qte)
                                }

                                if (!products.map(p => p.id).includes(r.article[0])) {
                                    products.push({id: r.article[0], name: r.article[1]})
                                }

                                if (r.tunnel_id) {
                                    if (!tunnels.map(t => t.id).includes(r.tunnel_id[0])) {
                                        tunnels.push({id: r.tunnel_id[0], name: r.tunnel_id[1]})
                                    }
                                }

                            })

                            $('#product_values').empty().append("<option value='0'> Product </option>");
                            products.map(e => {
                                $('#product_values').append("<option value='" + e.id + "'>" + e.name + "</option>");
                            })

                            $('#tunnel_values').empty().append("<option value='0'> Tunnel </option>");
                            tunnels.map(e => {
                                $('#tunnel_values').append("<option value='" + e.id + "'>" + e.name + "</option>");
                            })


                            $('#reception_prod').empty().append('<span>' + reception_prod.toFixed(2) + '</span>');
                            $('#reception_serv').empty().append('<span>' + reception_serv.toFixed(2) + '</span>');
                            $('#reception_total').empty().append('<span>' + Number(reception_prod + reception_serv).toFixed(2) + '</span>');

                            $('#treatment_prod').empty().append('<span>' + treatment_prod.toFixed(2) + '</span>');
                            $('#treatment_serv').empty().append('<span>' + treatment_serv.toFixed(2) + '</span>');
                            $('#treatment_total').empty().append('<span>' + Number(treatment_prod + treatment_serv).toFixed(2) + '</span>');

                            $('#tunnel_prod').empty().append('<span>' + tunnel_prod.toFixed(2) + '</span>');
                            $('#tunnel_serv').empty().append('<span>' + tunnel_serv.toFixed(2) + '</span>');
                            $('#tunnel_total').empty().append('<span>' + Number(tunnel_prod + tunnel_serv).toFixed(2) + '</span>');


                            $('#packaging_prod').empty().append('<span>' + packaging_prod.toFixed(2) + '</span>');
                            $('#packaging_serv').empty().append('<span>' + packaging_serv.toFixed(2) + '</span>');
                            $('#packaging_total').empty().append('<span>' + Number(packaging_prod + packaging_serv).toFixed(2) + '</span>');


                            //   Quality indicator chart
                            var ctx = document.getElementById("canvasQuality").getContext('2d');

                            const data = {
                                labels: qualities, // Add labels to array
                                datasets: [{
                                    label: 'My First Dataset',
                                    data: quality_data,
                                    backgroundColor: [
                                        'rgb(255, 99, 132)',
                                        'rgb(0,19,142)'],
                                    hoverOffset: 4
                                }]
                            }
                            window.myCharts = new Chart(ctx, {
                                type: 'pie',
                                data: data,
                                options: {
                                    responsive: true, // Instruct chart js to respond nicely.
                                    maintainAspectRatio: false, // Add to prevent default behaviour of full-width/height
                                }
                            });
                        })

                    //loading tunnel capacities
                    rpc.query({
                        model: "fishing.tunnel",
                        method: 'search_read',
                        args: [[], []],
                    })
                        .then(function (result) {
                            console.log(result)
                            let total_capacity = 0
                            result.map(t => {
                                total_capacity += t.capacity
                            })

                            $('#capacity').empty().append(total_capacity);

                        })

                    //loading performance data
                    rpc.query({
                        model: "fishing.time",
                        method: 'search_read',
                        args: [[], []],
                    })
                        .then(function (result) {
                            if (result.length > 2) {
                                console.log(result)


                                let tr_time = result.filter(t => t.operation === 'treatment')[0]
                                let tn_time = result.filter(t => t.operation === 'tunnel')[0]
                                let pk_time = result.filter(t => t.operation === 'packaging')[0]

                                rpc.query({
                                    model: "fishing.reception.detail",
                                    method: 'search_read',
                                    args: [[['status', '!=', '6']], []],
                                })
                                    .then(function (result) {
                                        var performance_rates = [];
                                        result.map(r => {
                                            let rec_tr_performance = 0
                                            let rec_tn_performance = 0
                                            let rec_pk_performance = 0

                                            if (r.startdate && r.end_date) {
                                                let theory_kg_time = tr_time.time / tr_time.qte
                                                let theory_rec_time = theory_kg_time * (r.qte + r.process_qty)
                                                let real_time = r.end_date - r.startdate
                                                let seconds = real_time.seconds
                                                real_time = (seconds % 3600) // 60
                                                rec_tr_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                                            }

                                            if (r.tunnel_start_date && r.tunnel_end_date) {
                                                let theory_kg_time = tn_time.time / tn_time.qte
                                                let theory_rec_time = theory_kg_time * r.qte
                                                let real_time = r.tunnel_end_date - r.tunnel_start_date
                                                let seconds = real_time.seconds
                                                real_time = (seconds % 3600) // 60
                                                rec_tn_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                                            }

                                            if (r.paking_start_date && r.paking_end_date) {
                                                let theory_kg_time = pk_time.time / pk_time.qte
                                                let theory_rec_time = theory_kg_time * (r.qte + r.process_qty)
                                                let real_time = r.paking_end_date - r.paking_start_date
                                                let seconds = real_time.seconds
                                                real_time = (seconds % 3600) // 60
                                                rec_pk_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                                            }

                                            let rec_performance = (rec_tr_performance + rec_tn_performance + rec_pk_performance) / 3

                                            performance_rates.push(rec_performance)
                                        })

                                        var sum = 0

                                        for (var i = 0; i < performance_rates.length; i++) {
                                            sum += performance_rates[i];
                                        }

                                        //   performance chart
                                        var ctx1 = document.getElementById("canvasTime").getContext('2d');
                                        const data1 = {
                                            labels: ['performance'],
                                            datasets: [{
                                                label: 'Rate',
                                                data: [sum / performance_rates.length],
                                                backgroundColor: [
                                                    'rgb(255, 99, 132)'
                                                ],
                                                borderColor: [
                                                    'rgb(153, 102, 255)',
                                                ],
                                                borderWidth: 1
                                            }]
                                        };
                                        window.myCharts = new Chart(ctx1, {
                                            type: 'bar',
                                            data: data1,
                                            options: {
                                                scales: {
                                                    yAxes: [{
                                                        ticks: {
                                                            suggestedMax: 100,
                                                            beginAtZero: true
                                                        }
                                                    }]
                                                }
                                            },
                                        });
                                    })
                            }
                            else {
                                //   performance chart
                                var ctx1 = document.getElementById("canvasTime").getContext('2d');
                                const data1 = {
                                    labels: ['performance'],
                                    datasets: [{
                                        label: 'Rate',
                                        data: [100],
                                        backgroundColor: [
                                            'rgb(255, 99, 132)'
                                        ],
                                        borderWidth: 1
                                    }]
                                };
                                window.myCharts = new Chart(ctx1, {
                                    type: 'bar',
                                    data: data1,
                                    options: {
                                        scales: {
                                            yAxes: [{
                                                ticks: {
                                                    suggestedMax: 100,
                                                    beginAtZero: true
                                                }
                                            }]
                                        }
                                    },
                                });
                            }
                        })

                    //refreshing data everytime the product filter changed
                    $('#product_values').on('change', function () {
                        const p_id = this.value;
                        product_id = p_id
                        //console.log("product chnged to : " product_id);
                        console.log("tn is : " + tunnel_id)

                        let args = [[['status', '!=', '6']], []]
                        if (tunnel_id != 0)
                            args[0].push(['tunnel_id', '=', Number(tunnel_id)])
                        if (p_id == 0) {
                            rpc.query({
                                model: "fishing.reception.detail",
                                method: 'search_read',
                                args: args,
                            })
                                .then(function (result) {
                                    // console.log(result)
                                    // Statistics data

                                    //reception
                                    let reception_prod = 0
                                    let reception_serv = 0

                                    //treatment
                                    let treatment_prod = 0
                                    let treatment_serv = 0

                                    //tunnel
                                    let tunnel_prod = 0
                                    let tunnel_serv = 0

                                    //pkging
                                    let packaging_prod = 0
                                    let packaging_serv = 0

                                    //   Quality indicator data
                                    let qualities = [];
                                    let quality_data = [];

                                    let products = [];

                                    result.map(r => {
                                        switch (r.status) {
                                            case '0':
                                                r.type == 'service' ? reception_serv += r.qte : reception_prod += r.qte
                                                break
                                            case '1':
                                                r.type == 'service' ? treatment_serv += r.qte : treatment_prod += r.qte
                                                break
                                            case '3':
                                                r.type == 'service' ? tunnel_serv += r.qte : tunnel_prod += r.qte
                                                break
                                            case '5':
                                                r.type == 'service' ? packaging_serv += r.qte : packaging_prod += r.qte
                                                break
                                        }
                                        if (qualities.includes(r.quality[1])) {
                                            let qindex = qualities.indexOf(r.quality[1])
                                            quality_data[qindex] += r.qte
                                        } else {
                                            qualities.push(r.quality[1]);
                                            quality_data.push(r.qte)
                                        }

                                        if (!products.map(p => p.id).includes(r.article[0])) {
                                            products.push({id: r.article[0], name: r.article[1]})
                                        }
                                    })

                                    $('#product_values').empty().append("<option value='0'> Product </option>");
                                    products.map(e => {
                                        $('#product_values').append("<option value='" + e.id + "'>" + e.name + "</option>");
                                    })


                                    $('#reception_prod').empty().append('<span>' + reception_prod + '</span>');
                                    $('#reception_serv').empty().append('<span>' + reception_serv + '</span>');
                                    $('#reception_total').empty().append('<span>' + Number(reception_prod + reception_serv) + '</span>');

                                    $('#treatment_prod').empty().append('<span>' + treatment_prod + '</span>');
                                    $('#treatment_serv').empty().append('<span>' + treatment_serv + '</span>');
                                    $('#treatment_total').empty().append('<span>' + Number(treatment_prod + treatment_serv) + '</span>');

                                    $('#tunnel_prod').empty().append('<span>' + tunnel_prod + '</span>');
                                    $('#tunnel_serv').empty().append('<span>' + tunnel_serv + '</span>');
                                    $('#tunnel_total').empty().append('<span>' + Number(tunnel_prod + tunnel_serv) + '</span>');


                                    $('#packaging_prod').empty().append('<span>' + packaging_prod + '</span>');
                                    $('#packaging_serv').empty().append('<span>' + packaging_serv + '</span>');
                                    $('#packaging_total').empty().append('<span>' + Number(packaging_prod + packaging_serv) + '</span>');


                                    //   Quality indicator chart
                                    let ctx = document.getElementById("canvasQuality").getContext('2d');

                                    const data = {
                                        labels: qualities, // Add labels to array
                                        datasets: [{
                                            label: 'My First Dataset',
                                            data: quality_data,
                                            backgroundColor: [
                                                'rgb(255, 99, 132)',
                                                'rgb(0,19,142)'],
                                            hoverOffset: 4
                                        }]
                                    }
                                    window.myCharts = new Chart(ctx, {
                                        type: 'pie',
                                        data: data,
                                        options: {
                                            responsive: true, // Instruct chart js to respond nicely.
                                            maintainAspectRatio: false, // Add to prevent default behaviour of full-width/height
                                        }
                                    });


                                    //   performance chart
                                    var ctx1 = document.getElementById("canvasTime").getContext('2d');

                                    window.myCharts = new Chart(ctx1, {
                                        type: 'bar',
                                        data: {
                                            labels: ["Performance"],
                                            datasets: [
                                                {
                                                    backgroundColor: "#ff6384",
                                                    data: [55],
                                                },
                                            ]
                                        },
                                        options: {
                                            title: {
                                                display: false,
                                                text: 'Population growth (millions): Europe & Africa'
                                            },
                                            legend: {display: false}
                                        }
                                    });
                                })
                        } else {
                            args[0].push(['article', '=', Number(p_id)])
                            rpc.query({
                                model: "fishing.reception.detail",
                                method: 'search_read',
                                args: args,
                            })
                                .then(function (result) {
                                    console.log(result)
                                    // Statistics data

                                    //reception
                                    var reception_prod = 0
                                    var reception_serv = 0

                                    //treatment
                                    var treatment_prod = 0
                                    var treatment_serv = 0

                                    //tunnel
                                    var tunnel_prod = 0
                                    var tunnel_serv = 0

                                    //pkging
                                    var packaging_prod = 0
                                    var packaging_serv = 0

                                    //   Quality indicator data
                                    var qualities = [];
                                    var quality_data = [];


                                    result.map(r => {
                                        switch (r.status) {
                                            case '0':
                                                r.type == 'service' ? reception_serv += r.qte : reception_prod += r.qte
                                                break
                                            case '1':
                                                r.type == 'service' ? treatment_serv += r.qte : treatment_prod += r.qte
                                                break
                                            case '3':
                                                r.type == 'service' ? tunnel_serv += r.qte : tunnel_prod += r.qte
                                                break
                                            case '5':
                                                r.type == 'service' ? packaging_serv += r.qte : packaging_prod += r.qte
                                                break
                                        }

                                        if (qualities.includes(r.quality[1])) {
                                            let qindex = qualities.indexOf(r.quality[1])
                                            quality_data[qindex] += r.qte
                                        } else {
                                            qualities.push(r.quality[1]);
                                            quality_data.push(r.qte)
                                        }
                                    })

                                    $('#reception_prod').empty().append('<span>' + reception_prod + '</span>');
                                    $('#reception_serv').empty().append('<span>' + reception_serv + '</span>');
                                    $('#reception_total').empty().append('<span>' + Number(reception_prod + reception_serv) + '</span>');

                                    $('#treatment_prod').empty().append('<span>' + treatment_prod + '</span>');
                                    $('#treatment_serv').empty().append('<span>' + treatment_serv + '</span>');
                                    $('#treatment_total').empty().append('<span>' + Number(treatment_prod + treatment_serv) + '</span>');

                                    $('#tunnel_prod').empty().append('<span>' + tunnel_prod + '</span>');
                                    $('#tunnel_serv').empty().append('<span>' + tunnel_serv + '</span>');
                                    $('#tunnel_total').empty().append('<span>' + Number(tunnel_prod + tunnel_serv) + '</span>');


                                    $('#packaging_prod').empty().append('<span>' + packaging_prod + '</span>');
                                    $('#packaging_serv').empty().append('<span>' + packaging_serv + '</span>');
                                    $('#packaging_total').empty().append('<span>' + Number(packaging_prod + packaging_serv) + '</span>');


                                    //   Quality indicator chart
                                    var ctx = document.getElementById("canvasQuality").getContext('2d');

                                    const data = {
                                        labels: qualities, // Add labels to array
                                        datasets: [{
                                            label: 'My First Dataset',
                                            data: quality_data,
                                            backgroundColor: [
                                                'rgb(255, 99, 132)',
                                                'rgb(0,19,142)'],
                                            hoverOffset: 4
                                        }]
                                    }
                                    window.myCharts = new Chart(ctx, {
                                        type: 'pie',
                                        data: data,
                                        options: {
                                            responsive: true, // Instruct chart js to respond nicely.
                                            maintainAspectRatio: false, // Add to prevent default behaviour of full-width/height
                                        }
                                    });

                                })
                        }
                    });

                    //refreshing freezing data everytime the tunnel filter changed
                    $('#tunnel_values').on('change', function () {
                        const t_id = this.value;
                        tunnel_id = t_id
                        console.log(tunnel_id);
                        let args = [[['status', '=', '3']], []]
                        if (product_id != 0)
                            args[0].push(['article', '=', Number(product_id)])

                        if (t_id == 0) {

                            rpc.query({
                                model: "fishing.reception.detail",
                                method: 'search_read',
                                args: args,
                            })
                                .then(function (result) {
                                    console.log(result)
                                    // Statistics data

                                    //tunnel
                                    var tunnel_prod = 0
                                    var tunnel_serv = 0

                                    result.map(r => {

                                        r.type == 'service' ? tunnel_serv += r.qte : tunnel_prod += r.qte
                                    })

                                    $('#tunnel_prod').empty().append('<span>' + tunnel_prod + '</span>');
                                    $('#tunnel_serv').empty().append('<span>' + tunnel_serv + '</span>');
                                    $('#tunnel_total').empty().append('<span>' + Number(tunnel_prod + tunnel_serv) + '</span>');
                                })


                            //loading tunnel capacities
                            rpc.query({
                                model: "fishing.tunnel",
                                method: 'search_read',
                                args: [[], []],
                            })
                                .then(function (result) {
                                    console.log(result)
                                    let total_capacity = 0
                                    result.map(t => {
                                        total_capacity += t.capacity
                                    })

                                    $('#capacity').empty().append(total_capacity);

                                })

                        } else {
                            args[0].push(['tunnel_id', '=', Number(t_id)])

                            rpc.query({
                                model: "fishing.reception.detail",
                                method: 'search_read',
                                args: args,
                            })
                                .then(function (result) {
                                    console.log(result)
                                    // Statistics data

                                    //tunnel
                                    var tunnel_prod = 0
                                    var tunnel_serv = 0

                                    result.map(r => {

                                        r.type == 'service' ? tunnel_serv += r.qte : tunnel_prod += r.qte
                                    })

                                    $('#tunnel_prod').empty().append('<span>' + tunnel_prod + '</span>');
                                    $('#tunnel_serv').empty().append('<span>' + tunnel_serv + '</span>');
                                    $('#tunnel_total').empty().append('<span>' + Number(tunnel_prod + tunnel_serv) + '</span>');
                                })

                            rpc.query({
                                model: "fishing.tunnel",
                                method: 'search_read',
                                args: [[['id', '=', Number(t_id)]], []],
                            })
                                .then(function (result) {
                                    //console.log(result)
                                    $('#capacity').empty().append('<span>' + result[0].capacity + '</span>');

                                })
                        }
                    });

                    let total_serv_stock = 0;
                    let total_prod_stock = 0;


                    //getting service stock
                    rpc.query({
                        model: "fish.service.stock",
                        method: 'search_read',
                        args: [[['is_out', '=', false]], []],
                    })
                        .then(function (result) {
                            result.map(e => total_serv_stock += e.qte);
                            $('#service_stock').empty().append(total_serv_stock);
                        })


                    //getting production stock
                    rpc.query({
                        model: "product.product",
                        method: 'search_read',
                        args: [[], []],
                    })
                        .then(function (result) {
                            result
                                .filter(p => p.categ_id[1].includes('Fish') && p.name !== 'Fish')
                                .map(p => total_prod_stock += p.free_qty)
                            $('#prod_stock').empty().append(total_prod_stock);
                        })
                        .then(res => {
                            //getting total stock capacity
                            let total_stock_capacity = 0
                            rpc.query({
                                model: "stock.location",
                                method: 'search_read',
                                args: [[], []],
                            })
                                .then(function (result) {
                                    result.map(e => total_stock_capacity += e.capacity_unit)
                                    $('#total_stock_capacity').empty().append(total_stock_capacity);

                                    $('#real_stock').empty().append(Number(total_serv_stock) + Number(total_prod_stock));

                                    $('#free_stock').empty().append(total_stock_capacity - (Number(total_serv_stock) + Number(total_prod_stock)));
                                    let occupation_rate = ((Number(total_serv_stock) + Number(total_prod_stock)) * 100) / total_stock_capacity
                                    $('#occupation_rate').empty()
                                        .append(`
                                         <div class="progress">
                                                  <div class="progress-bar" role="progressbar" style="width: ${occupation_rate}%"
                                                       aria-valuenow="${occupation_rate}" aria-valuemin="0"
                                                       aria-valuemax="100">
                                                       ${occupation_rate.toFixed(2)}%
                                                       </div>
                                         </div>
                                        `);
                                })
                        })
                });
        },
    });
    core.action_registry.add('fish_dashboard', ActionMenu);

});