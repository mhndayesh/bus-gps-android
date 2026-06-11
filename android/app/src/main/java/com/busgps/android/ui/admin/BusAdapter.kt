package com.busgps.android.ui.admin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemBusBinding
import com.busgps.android.model.Bus

class BusAdapter(
    private val buses: List<Bus>,
    private val onAssignDriver: (Int) -> Unit
) : RecyclerView.Adapter<BusAdapter.VH>() {

    inner class VH(val binding: ItemBusBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemBusBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = buses.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val bus = buses[position]
        holder.binding.apply {
            tvPlate.text = bus.plate
            tvBusId.text = "Bus #${bus.id}"
            btnAssignDriver.setOnClickListener { onAssignDriver(bus.id) }
        }
    }
}
