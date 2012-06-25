$(document).ready(function() {
    $(":radio[@id^='action_']").each(function(index) {
        $(this).change(function() {
            if($(this).attr("id") == "action_split") {
                $("#split-controls").show();
            }
            else {
                $("#split-controls").hide();
            }
        });
    });
});

$(document).ready(function() {
    $("#toggle-split-options").toggle(function() {
        var splits = $("#input-existing-tickets").val().split(", ");
        $(".split-option-check").each(function(index) {
            var splitOptionId = $(this).attr("id").match(/\d+/)[0];
            
            if (splits.indexOf(splitOptionId) > -1) {
                $(this).attr("checked", "true");
            }
            else {
                $(this).removeAttr("checked");
            }
        });
        $(this).text("hide ticket list");
        $("#split-options").show();
    }, function() {
        $(this).text("choose from list");
        $("#split-options").hide();
    });
});

$(document).ready(function() {
    $(".split-option-check").each(function(index) {
        $(this).change(function() {
            var checked = new Array();
            $(".split-option-check:checked").each(function(index) {
                var id = $(this).attr("id").match(/\d+/)[0];
                checked.push(id);
            });
            $("#input-existing-tickets").val(checked.join(", "));
        });
    });
});

$(document).ready(function() {
    $("#add-ticket").click(function(event) {
        event.preventDefault();
        var ticket = $("#new-tickets").children().first().clone(true);

        // clear field values for new ticket
        ticket.children(".input-summary").val("");
        ticket.children(".select-milestone").children().first().attr("selected", "true");
        ticket.children(".select-component").children().first().attr("selected", "true");

        $("#new-tickets").append(ticket);
    });

    $(".remove-ticket").click(function(event) {
        event.preventDefault();
        var ticket = $(this).parent();

        // if ticket is the only new ticket, clear all input fields for ticket 
        if ($("#new-tickets").children().size() == 1) {
            ticket.children(".input-summary").val("");
            ticket.children(".select-milestone").children().first().attr("selected", "true");
            ticket.children(".select-component").children().first().attr("selected", "true");
            return false;
        }

        // otherwise, completely remove input fields for ticket from the new tickets list
        ticket.remove();
    });

    $("#propertyform").submit(function(event) {
        var newTickets = $("#new-tickets").children();
        
        newTickets.each(function(index) {
            var summary = $(this).children(".input-summary");
            var milestone = $(this).children(".select-milestone");
            var component = $(this).children(".select-component");
           
            if (summary.val() && milestone.prop("selectedIndex") > 0 || component.prop("selectedIndex") > 0) {
                // assign unique name attributes to each new ticket field
                summary.attr("name", "field_split_new_" + index + "_summary");
                milestone.attr("name", "field_split_new_" + index + "_milestone");
                component.attr("name", "field_split_new_" + index + "_component");
            }
        });
    }); 
});
