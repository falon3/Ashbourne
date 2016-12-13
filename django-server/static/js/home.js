// FOR NAVIGATION BUTTONS AT TOP OF PAGE
$(document).ready(function () {
    $(".time_picker").datetimepicker();
    
    $(document).on('click', '.map', function () {
        $(location).attr('href',"/map/");
    });


    $(document).on('click', '#people', function () {

        $.ajax({
            url: "/get_people_table/",
            traditional: true,
            async: false,
            type: "GET",
            dataType: "json",
            data: {
                hash: 'something'
            },
            success: function (data) {
                console.log(data['html'])
                $('.report-content').replaceWith(data['html']);
                $('.report-content').show();
            },
            failure: function (data) {
                console.log('Got an error when requesting show_activity_table');
            }
        });
    });
    $(document).on('click', '.relation-clicked', function () {
        $.ajax({
            url: "/get_relations_table/",
            traditional: true,
            async: false,
            type: "GET",
            dataType: "json",
            data: {
                person_hash: $(this).data('id')
            },
            success: function (data) {
                $('.relation-table').html(data['html']);
            },
            failure: function (data) {
                console.log('Got an error when requesting show_activity_table');
            }
        });
    });
    // {        
    //     $(document).on('click', ".submit_button", function () {}
    //                    {            console.log('we are clicked!')}
    //                         {            $.ajax({}
    //                                             {               url: "/query_activities/",}
    //                                             {                traditional: true,}
    //                                             {                async: false,}
    //                                             {                type: "GET",}
    //                                             {                dataType: "json",}
    //                                             {                data: {}
    //                                                              {                    person_hash: $("#person-select").data('id'),}
    //                                                              {                    location: $("#location-select").data('id'),}
    //                                                              {                    from_time: $("#time-from").val(),}
    //                                                              {                   to_time: $("#time-to").val()}
    //                                                              {                },}
    //                                             {                success: function (data) {}
    //                                                              {                    console.log('we were successfull!!!!!!!!!!!!!!!!!!!')}
    //                                                              {                    $('#activity-table').html(data['html']);}
    //                                                              {                },}
    //                                             {                failure: function (data) {}
    //                                                              {                    console.log('Got an error when requesting show_activity_table');}
    //                                                              {                }}
    //                                             {            });}
    //                         {        });}

});
