
/* Please use this command to compile this file into the parent `js` directory:
    coffee --no-header -w -o ../ -c bika.lims.utils.calcs.coffee
 */

(function() {
  var bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; },
    slice = [].slice;

  window.CalculationUtils = (function() {
    function CalculationUtils() {
      this.post_results = bind(this.post_results, this);
      this.on_update_success = bind(this.on_update_success, this);
      this.collect_form_results = bind(this.collect_form_results, this);
      this.clear_alerts = bind(this.clear_alerts, this);
      this.all_results_captured = bind(this.all_results_captured, this);
      this.on_result_change = bind(this.on_result_change, this);
      this.on_result_blur = bind(this.on_result_blur, this);
      this.on_result_focus = bind(this.on_result_focus, this);
      this.debounce = bind(this.debounce, this);
      this.bind_eventhandler = bind(this.bind_eventhandler, this);
      this.load = bind(this.load, this);
    }

    CalculationUtils.prototype.load = function() {
      console.debug("CalculationUtils::load");
      $(".state-retracted .ajax_calculate").removeClass('ajax_calculate');
      this.bind_eventhandler();
    };

    CalculationUtils.prototype.bind_eventhandler = function() {

      /*
       * Binds callbacks on elements
       */
      console.debug("CalculationUtils::bind_eventhandler");
      $('body').on('focus', '.ajax_calculate', this.debounce(this.on_result_focus));
      $('body').on('blur', '.ajax_calculate', this.debounce(this.on_result_blur));
      $('body').on('change', '.ajax_calculate', this.debounce(this.on_result_change));
    };

    CalculationUtils.prototype.debounce = function(func, threshold, execAsap) {

      /*
       * Debounce a function call
       * See: https://coffeescript-cookbook.github.io/chapters/functions/debounce
       */
      var timeout;
      timeout = null;
      return function() {
        var args, delayed, obj;
        args = 1 <= arguments.length ? slice.call(arguments, 0) : [];
        obj = this;
        delayed = function() {
          if (!execAsap) {
            func.apply(obj, args);
          }
          return timeout = null;
        };
        if (timeout) {
          clearTimeout(timeout);
        } else if (execAsap) {
          func.apply(obj, args);
        }
        return timeout = setTimeout(delayed, threshold || 100);
      };
    };

    CalculationUtils.prototype.on_result_focus = function(event) {

      /*
       * Eventhandler when Result field get focus
       */
      var el;
      console.debug("CalculationUtils::on_result_focus");
      el = event.currentTarget;
      $(el).attr('focus_value', $(el).val());
      $(el).addClass("ajax_calculate_focus");
    };

    CalculationUtils.prototype.on_result_blur = function(event) {

      /*
       * Eventhandler when Result field looses focus and 
       * the value did not change
       */
      var el;
      console.debug("CalculationUtils::on_result_blur");
      el = event.currentTarget;
      if ($(el).attr('focus_value') === $(el).val()) {
        $(el).removeAttr("focus_value");
        $(el).removeClass("ajax_calculate_focus");
      }
    };

    CalculationUtils.prototype.on_result_change = function(event) {

      /*
       * Eventhandler when Result field looses focus and 
       * the value has change
       */
      var el, field, form, item_data, results, uid, value;
      console.debug("CalculationUtils::on_result_change");
      el = event.currentTarget;
      form = $(el).parents("form");
      if (this.all_results_captured(form) === false) {
        return;
      }
      $(el).removeAttr("focus_value");
      $(el).removeClass("ajax_calculate_focus");
      uid = $(el).attr('uid');
      field = $(el).attr('field');
      value = $(el).attr('value');
      item_data = $(el).parents('table').prev('input[name="item_data"]').val();
      this.clear_alerts(el, item_data, uid);
      results = this.collect_form_results();
      this.post_results(form, uid, field, value, item_data, results);
    };

    CalculationUtils.prototype.all_results_captured = function(form) {
      var i, results;
      results = form.find('.ajax_calculate');
      for (i in results) {
        if (results[i].value && results[i].value.length === 0) {
          return false;
        }
      }
      return true;
    };

    CalculationUtils.prototype.clear_alerts = function(element, item_data, uid) {

      /*
       * clear out the alerts for this field
       * add value to form's item_data for each interim field
       */
      var i;
      console.debug("CalculationUtils::clear_alerts");
      $(".bika-alert").filter("span[uid='" + uid + "']").empty();
      if ($(element).parents('td,div').first().hasClass('interim')) {
        item_data = $.parseJSON(item_data);
        for (i in item_data[uid]) {
          if (item_data[uid][i]['keyword'] === field) {
            item_data[uid][i]['value'] = value;
            item_data = $.toJSON(item_data);
            $(element).parents('table').prev('input[name="item_data"]').val(item_data);
            break;
          }
        }
      }
    };

    CalculationUtils.prototype.collect_form_results = function() {

      /*
       * collect all form results into a hash (by analysis UID)
       */
      var results;
      results = {};
      $.each($("td:not(.state-retracted) input[field='Result'], td:not(.state-retracted) select[field='Result']"), function(i, e) {
        var andls, defandls, dlop, mapping, res, result, tryldl, tryudl, uid;
        uid = $(e).attr('uid');
        result = $(e).val().trim();
        defandls = {
          default_ldl: 0,
          default_udl: 100000,
          dlselect_allowed: false,
          manual_allowed: false,
          is_ldl: false,
          is_udl: false,
          below_ldl: false,
          above_udl: false
        };
        andls = $('input[id^="AnalysisDLS."][uid="' + uid + '"]');
        andls = andls.length > 0 ? andls.first().val() : null;
        andls = andls !== null ? $.parseJSON(andls) : defandls;
        dlop = $('select[name^="DetectionLimit."][uid="' + uid + '"]');
        if (dlop.length > 0) {
          andls.is_ldl = false;
          andls.is_udl = false;
          andls.below_ldl = false;
          andls.above_udl = false;
          tryldl = result.lastIndexOf('<', 0) === 0;
          tryudl = result.lastIndexOf('>', 0) === 0;
          if (tryldl || tryudl) {
            res = result.substring(1);
            if (!isNaN(parseFloat(res))) {
              result = '' + parseFloat(res);
              if (andls.manual_allowed === true) {
                andls.is_ldl = tryldl;
                andls.is_udl = tryudl;
                andls.below_ldl = tryldl;
                andls.above_udl = tryudl;
              } else {
                $(e).val(result);
              }
            }
          } else {
            andls.is_ldl = false;
            andls.is_udl = false;
            andls.below_ldl = false;
            andls.above_udl = false;
            if (!isNaN(parseFloat(result))) {
              dlop = dlop.first().val().trim();
              if (dlop === '<' || dlop === '>') {
                andls.is_ldl = dlop === '<';
                andls.is_udl = dlop === '>';
                andls.below_ldl = andls.is_ldl;
                andls.above_udl = andls.is_udl;
              } else {
                result = parseFloat(result);
                andls.below_ldl = result < andls.default_ldl;
                andls.above_udl = result > andls.default_udl;
                result = '' + result;
              }
            }
          }
        } else if (!isNaN(parseFloat(result))) {
          result = parseFloat(result);
          andls.is_ldl = false;
          andls.is_udl = false;
          andls.below_ldl = result < andls.default_ldl;
          andls.above_udl = result > andls.default_udl;
          result = '' + result;
        }
        mapping = {
          keyword: $(e).attr('objectid'),
          result: result,
          isldl: andls.is_ldl,
          isudl: andls.is_udl,
          ldl: andls.is_ldl ? result : andls.default_ldl,
          udl: andls.is_udl ? result : andls.default_udl,
          belowldl: andls.below_ldl,
          aboveudl: andls.above_udl
        };
        results[uid] = mapping;
      });
      return results;
    };

    CalculationUtils.prototype.on_update_success = function(form, data) {

      /*
       * clear out all row alerts for rows with fresh results
       */
      var i, result, u;
      console.debug("CalculationUtils::on_update_success");
      for (i in $(data['results'])) {
        result = $(data['results'])[i];
        $(".bika-alert").filter("span[uid='" + result.uid + "']").empty();
      }
      $.each(data['alerts'], function(auid, alerts) {
        var lert;
        for (i in alerts) {
          lert = alerts[i];
          $("span[uid='" + auid + "']").filter("span[field='" + lert.field + "']").append("<img src='" + window.portal_url + "/" + lert.icon + "' title='" + lert.msg + "' uid='" + auid + "'/>");
        }
      });
      for (i in $(data['uncertainties'])) {
        u = $(data['uncertainties'])[i];
        $('#' + u.uid + "-uncertainty").val(u.uncertainty);
        $('[uid="' + u.uid + '"][field="Uncertainty"]').val(u.uncertainty);
      }
      for (i in $(data['results'])) {
        result = $(data['results'])[i];
        $("input[uid='" + result.uid + "']").filter("input[field='Result']").val(result.result);
        $('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").val(result.dry_result);
        $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").siblings()[0]).empty().append(result.dry_result);
        if (result.dry_result !== '') {
          $($('[type="hidden"]').filter("[field='ResultDM']").filter("[uid='" + result.uid + "']").siblings().filter(".after")).empty().append("<em class='discreet'>%</em>");
        }
        $("input[uid='" + result.uid + "']").filter("input[field='formatted_result']").val(result.formatted_result);
        $("span[uid='" + result.uid + "']").filter("span[field='formatted_result']").empty().append(result.formatted_result);
        if (result.result !== '' && result.result !== "") {
          if ($("[id*='cb_" + result.uid + "']").prop("checked") === false) {
            $("[id*='cb_" + result.uid + "']").prop('checked', true);
          }
        }
      }
      if ($('.ajax_calculate_focus').length > 0) {
        if ($(form).attr('submit_after_calculation')) {
          $('#submit_transition').click();
        }
      }
    };

    CalculationUtils.prototype.post_results = function(form, uid, field, value, item_data, results) {

      /*
       * post all collected results to the backend with the current result's metadata
       */
      var options, that;
      console.debug("CalculationUtils::post_results");
      that = this;
      options = {
        type: 'POST',
        url: 'listing_string_entry',
        data: {
          '_authenticator': $('input[name="_authenticator"]').val(),
          'uid': uid,
          'field': field,
          'value': value,
          'item_data': item_data,
          'results': $.toJSON(results),
          'specification': $(".specification").filter(".selected").attr("value")
        },
        dataType: "json",
        success: function(data, textStatus, $XHR) {
          that.on_update_success(form, data);
        }
      };
      $.ajax(options);
    };

    return CalculationUtils;

  })();

}).call(this);
