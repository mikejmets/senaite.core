### Please use this command to compile this file into the parent `js` directory:
    coffee --no-header -w -o ../ -c bika.lims.utils.calcs.coffee
###


window.CalculationUtils = ->
    that = this

    that.load = ->

        $(".state-retracted .ajax_calculate").removeClass 'ajax_calculate'

        $(".ajax_calculate").live 'focus', ->
            $(this).attr 'focus_value', $(this).val()
            $(this).addClass "ajax_calculate_focus"
            return

        # 'blur' handler only if the value did NOT change
        $(".ajax_calculate").live 'blur', ->
            if $(this).attr('focus_value') == $(this).val()
                $(this).removeAttr "focus_value"
                $(this).removeClass "ajax_calculate_focus"
            return

        # otherwise 'change' handler is fired.
        $(".ajax_calculate").live 'change', ->
            $(this).removeAttr "focus_value"
            $(this).removeClass "ajax_calculate_focus"

            form = $(this).parents("form")
            uid = $(this).attr('uid')
            field = $(this).attr('field')
            value = $(this).attr('value')
            item_data = $(this).parents('table').prev('input[name="item_data"]').val()

            # clear out the alerts for this field
            $(".bika-alert").filter("span[uid='"+uid+"']").empty()

            if $(this).parents('td,div').first().hasClass('interim')
                # add value to form's item_data
                item_data = $.parseJSON(item_data)
                for i of item_data[uid]
                    if item_data[uid][i]['keyword'] == field
                        item_data[uid][i]['value'] = value
                        item_data = $.toJSON(item_data)
                        $(this).parents('table').prev('input[name="item_data"]').val(item_data)
                        break

            # collect all form results into a hash (by analysis UID)
            results = {}
            $.each $("td:not(.state-retracted) input[field='Result'], td:not(.state-retracted) select[field='Result']"), (i, e) ->
                local_uid = $(e).attr('uid')
                result = $(e).val().trim()

                # LIMS-1769. Allow to use LDL and UDL in calculations.
                # https://jira.bikalabs.com/browse/LIMS-1769
                #
                # LIMS-1775. Allow to select LDL or UDL defaults in
                # results with readonly mode
                # https://jira.bikalabs.com/browse/LIMS-1775
                defandls = 
                    default_ldl: 0
                    default_udl: 100000
                    dlselect_allowed:  false
                    manual_allowed: false
                    is_ldl: false
                    is_udl: false
                    below_ldl: false
                    above_udl: false

                andls = $('input[id^="AnalysisDLS."][uid="'+local_uid+'"]')
                andls = if andls.length > 0 then andls.first().val() else null
                andls = if andls != null then $.parseJSON(andls) else defandls
                dlop = $('select[name^="DetectionLimit."][uid="'+local_uid+'"]')
                if dlop.length > 0
                    # If the analysis is under edition, give priority to
                    # the current values instead of AnalysisDLS values
                    andls.is_ldl = false
                    andls.is_udl = false
                    andls.below_ldl = false
                    andls.above_udl = false
                    tryldl = result.lastIndexOf('<', 0) == 0
                    tryudl = result.lastIndexOf('>', 0) == 0
                    if tryldl || tryudl
                        # Trying to create a DL directly?
                        res = result.substring(1)
                        if !isNaN(parseFloat(res))
                            result = ''+parseFloat(res)
                            if andls.manual_allowed == true
                                # Yep, a manually created DL
                                andls.is_ldl = tryldl
                                andls.is_udl = tryudl
                                andls.below_ldl = tryldl
                                andls.above_udl = tryudl
                            else
                                # Unexpected case or Indeterminate result.
                                # Although the selection of DL is allowed (DL
                                # selection list displayed) and the manual
                                # entry of DL is not allowed, the user has not
                                # selected a LD option from the list and has
                                # set a manual DL value in the result's input
                                # field. Remove the operator
                                $(e).val(result)
                    else
                        # LD set via selector
                        andls.is_ldl = false
                        andls.is_udl = false
                        andls.below_ldl = false
                        andls.above_udl = false
                        if !isNaN(parseFloat(result))
                            dlop = dlop.first().val().trim()
                            if dlop == '<' || dlop == '>'
                                # The result is a Detection Limit
                                andls.is_ldl = dlop == '<'
                                andls.is_udl = dlop == '>'
                                andls.below_ldl = andls.is_ldl
                                andls.above_udl = andls.is_udl
                            else 
                                # Regular result
                                result = parseFloat(result)
                                andls.below_ldl = result < andls.default_ldl
                                andls.above_udl = result > andls.default_udl
                                result = ''+result
                else if !isNaN(parseFloat(result)) 
                    # DL List not available and regular result
                    result = parseFloat(result)
                    andls.is_ldl = false
                    andls.is_udl = false
                    andls.below_ldl = result < andls.default_ldl
                    andls.above_udl = result > andls.default_udl
                    result = ''+result

                mapping = 
                    keyword:  $(e).attr('objectid')
                    result:   result
                    isldl:    andls.is_ldl
                    isudl:    andls.is_udl
                    ldl:      if andls.is_ldl then result else andls.default_ldl
                    udl:      if andls.is_udl then result else andls.default_udl
                    belowldl: andls.below_ldl
                    aboveudl: andls.above_udl

                results[local_uid] = mapping
                return

            options = 
                type: 'POST'
                url: 'listing_string_entry'
                data: 
                    '_authenticator': $('input[name="_authenticator"]').val()
                    'uid': uid
                    'field': field
                    'value': value
                    'results': $.toJSON(results)
                    'item_data': item_data
                    'specification': $(".specification").filter(".selected").attr("value")
                dataType: "json"
                success: (data, textStatus, $XHR) ->
                    # clear out all row alerts for rows with fresh results
                    for i of $(data['results'])
                        result = $(data['results'])[i]
                        $(".bika-alert").filter("span[uid='"+result.uid+"']").empty()

                    # put new alerts
                    $.each data['alerts'], (auid, alerts) ->
                        for i of alerts
                            lert = alerts[i]
                            $("span[uid='"+auid+"']")
                                .filter("span[field='"+lert.field+"']")
                                .append("<img src='"+window.portal_url+"/"+lert.icon+
                                    "' title='"+lert.msg+
                                    "' uid='"+auid+
                                    "'/>")
                        return

                    # Update uncertainty value
                    for i of $(data['uncertainties'])
                        u = $(data['uncertainties'])[i]
                        $('#'+u.uid+"-uncertainty").val(u.uncertainty)
                        $('[uid="'+u.uid+'"][field="Uncertainty"]').val(u.uncertainty)
                    
                    # put result values in their boxes
                    for i of $(data['results'])
                        result = $(data['results'])[i]
                        $("input[uid='"+result.uid+"']").filter("input[field='Result']").val(result.result)

                        $('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='"+result.uid+"']").val(result.dry_result)
                        $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='"+result.uid+"']").siblings()[0]).empty().append(result.dry_result)
                        if result.dry_result != ''
                            $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='"+result.uid+"']").siblings().filter(".after")).empty().append("<em class='discreet'>%</em>")
                        

                        $("input[uid='"+result.uid+"']").filter("input[field='formatted_result']").val(result.formatted_result)
                        $("span[uid='"+result.uid+"']").filter("span[field='formatted_result']").empty().append(result.formatted_result)

                        # check box
                        if result.result != '' && result.result != ""
                            if $("[id*='cb_"+result.uid+"']").prop("checked") == false
                                $("[id*='cb_"+result.uid+"']").prop('checked', true)

                    if $('.ajax_calculate_focus').length > 0
                        if $(form).attr 'submit_after_calculation'
                            $('#submit_transition').click()
                    return
            $.ajax(options)
            return
        return
    return
