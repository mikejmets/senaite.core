### Please use this command to compile this file into the parent `js` directory:
    coffee --no-header -w -o ../ -c bika.lims.utils.calcs.coffee
###


class window.CalculationUtils

  load: =>
    console.debug "CalculationUtils::load"

    $(".state-retracted .ajax_calculate").removeClass 'ajax_calculate'

    # bind the event handler to the elements
    @bind_eventhandler()

    return


  bind_eventhandler: =>
    ###
     * Binds callbacks on elements
    ###
    console.debug "CalculationUtils::bind_eventhandler"

    # result gets focus
    $('body').on 'focus', '.ajax_calculate', @debounce @on_result_focus

    # result looses focus but value hasn't changed
    $('body').on 'blur', '.ajax_calculate', @debounce @on_result_blur

    # result value has changes
    $('body').on 'change', '.ajax_calculate', @debounce @on_result_change

    return

  debounce: (func, threshold, execAsap) =>
    ###
     * Debounce a function call
     * See: https://coffeescript-cookbook.github.io/chapters/functions/debounce
    ###
    timeout = null

    (args...) ->
      obj = this
      delayed = ->
        func.apply(obj, args) unless execAsap
        timeout = null
      if timeout
        clearTimeout(timeout)
      else if (execAsap)
        func.apply(obj, args)
      timeout = setTimeout delayed, threshold || 100

    return


  on_result_focus: (event) =>
    ###
     * Eventhandler when Result field get focus
    ###
    console.debug "CalculationUtils::on_result_focus"
    el = event.currentTarget

    $(el).attr 'focus_value', $(el).val()
    $(el).addClass "ajax_calculate_focus"
    return


  on_result_blur: (event) =>
    ###
     * Eventhandler when Result field looses focus and 
     * the value did not change
    ###
    console.debug "CalculationUtils::on_result_blur"
    el = event.currentTarget
    if $(el).attr('focus_value') == $(el).val()
      $(el).removeAttr "focus_value"
      $(el).removeClass "ajax_calculate_focus"
    return


  on_result_change: (event) =>
    ###
     * Eventhandler when Result field looses focus and 
     * the value has change
    ###
    console.debug "CalculationUtils::on_result_change"
    el = event.currentTarget
    form = $(el).parents("form")
    
    # collect all form results into a hash (by analysis UID)
    results = @collect_form_results()

    # collect all interim results
    interims = $('input[interim="true"]');

    if @all_results_captured(results, interims) == false
      return
      
    $(el).removeAttr "focus_value"
    $(el).removeClass "ajax_calculate_focus"

    uid = $(el).attr('uid')
    field = $(el).attr('field')
    value = $(el).attr('value')
    item_data = $(el).parents('table').prev('input[name="item_data"]').val()

    # clear alerts and add value to any interim field
    @clear_alerts el, field, value, item_data, uid

    # post result to backend via ajax
    @post_results form, uid, field, value, item_data, results

    return


  all_results_captured: (results, interims) =>
    # return false if any interim results are empty
    for i of interims
        if interims[i].value == "0.0"
            console.debug 'CalculationUtils: all_results_captured returned false: ' + interims[i].getAttribute('field')
            return false

    # return false if any non interim results are empty
    for i of results
      if results[i].type != 'hidden' && results[i].result.length == 0
        console.debug 'CalculationUtils: all_results_captured returned false: ' + results[i]['keyword']
        return false

    console.debug 'CalculationUtils: all_results_captured returned true'
    return true

  clear_alerts: (element, field, value, item_data, uid) =>
    ###
     * clear out the alerts for this field
     * add value to form's item_data for each interim field
    ###
    console.debug "CalculationUtils::clear_alerts"

    $(".bika-alert").filter("span[uid='"+uid+"']").empty()

    if $(element).parents('td,div').first().hasClass('interim')
        item_data = $.parseJSON(item_data)
        for i of item_data[uid]
            if item_data[uid][i]['keyword'] == field
                item_data[uid][i]['value'] = value
                item_data = $.toJSON(item_data)
                $(element).parents('table').prev('input[name="item_data"]').val(item_data)
                break
    return


  collect_form_results: =>
    ###
     * collect all form results into a hash (by analysis UID)
    ###
    #
    results = {}
    $.each $("td:not(.state-retracted) input[interim='true'], td:not(.state-retracted) input[field='Result'], td:not(.state-retracted) select[field='Result']"), (i, e) ->
      uid = $(e).attr('uid')
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

      andls = $('input[id^="AnalysisDLS."][uid="'+uid+'"]')
      andls = if andls.length > 0 then andls.first().val() else null
      andls = if andls != null then $.parseJSON(andls) else defandls
      dlop = $('select[name^="DetectionLimit."][uid="'+uid+'"]')
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
          type: this.type

      console.debug 'CalculationUtils: collect_form_results ' + Object.keys(results).length
      results[uid] = mapping
      return
    return results


  on_update_success: (form, data) =>
    ###
     * clear out all row alerts for rows with fresh results
    ###
    console.debug "CalculationUtils::on_update_success"
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


  post_results: (form, uid, field, value, item_data, results) =>
    ###
     * post all collected results to the backend with the current result's metadata
    ###
    console.debug "CalculationUtils::post_results"
    that = this
    options = 
        type: 'POST'
        url: 'listing_string_entry'
        data: 
            '_authenticator': $('input[name="_authenticator"]').val()
            'uid': uid
            'field': field
            'value': value
            'item_data': item_data
            'results': $.toJSON(results)
            'specification': $(".specification").filter(".selected").attr("value")
        dataType: "json"
        success: (data, textStatus, $XHR) ->
          that.on_update_success form, data
          return
    $.ajax(options)
    return

